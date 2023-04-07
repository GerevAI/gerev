import datetime
import logging
import time
from dataclasses import dataclass
from http.client import IncompleteRead
from typing import Optional, Dict, List

from retry import retry
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, BaseDataSourceConfig
from data_source.api.basic_document import DocumentType, BasicDocument
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)


@dataclass
class SlackConversation:
    id: str
    name: str


@dataclass
class SlackAuthor:
    name: str
    image_url: str


class SlackConfig(BaseDataSourceConfig):
    token: str


class SlackDataSource(BaseDataSource):
    FEED_BATCH_SIZE = 500

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Bot User OAuth Token", name="token", type=HTMLInputType.PASSWORD)
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        slack_config = SlackConfig(**config)
        slack = WebClient(token=slack_config.token)
        slack.auth_test()

    @staticmethod
    def _is_valid_message(message: Dict) -> bool:
        return 'client_msg_id' in message

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        slack_config = SlackConfig(**self._raw_config)
        self._slack = WebClient(token=slack_config.token)
        self._authors_cache: Dict[str, SlackAuthor] = {}

    def _list_conversations(self) -> List[SlackConversation]:
        conversations = self._slack.conversations_list(exclude_archived=True, limit=1000)
        return [SlackConversation(id=conv['id'], name=conv['name'])
                for conv in conversations['channels']]

    def _join_conversations(self, conversations: List[SlackConversation]) -> List[SlackConversation]:
        joined_conversations = []

        for conv in conversations:
            try:
                result = self._slack.conversations_join(channel=conv.id)
                if result['ok']:
                    logger.info(f'Joined channel {conv.name}')
                    joined_conversations.append(conv)
            except Exception as e:
                logger.warning(f'Could not join channel {conv.name}: {e}')

        return joined_conversations

    def _get_author_details(self, author_id: str) -> SlackAuthor:
        author = self._authors_cache.get(author_id, None)
        if author is None:
            author_info = self._slack.users_info(user=author_id)
            user = author_info['user']
            name = user.get('real_name') or user.get('name') or user.get('profile', {}).get('display_name') or 'Unknown'
            author = SlackAuthor(name=name,
                                 image_url=author_info['user']['profile']['image_72'])
            self._authors_cache[author_id] = author

        return author

    def _feed_new_documents(self) -> None:
        conversations = self._list_conversations()
        logger.info(f'Found {len(conversations)} conversations')

        joined_conversations = self._join_conversations(conversations)
        logger.info(f'Joined {len(joined_conversations)} conversations')

        for conv in joined_conversations:
            self.add_task_to_queue(self._feed_conversation, conv=conv)

    def _feed_conversation(self, conv: SlackConversation):
        logger.info(f'Feeding conversation {conv.name}')

        last_msg: Optional[BasicDocument] = None

        messages = self._fetch_conversation_messages(conv)
        for message in messages:
            if not self._is_valid_message(message):
                if last_msg is not None:
                    IndexQueue.get_instance().put_single(doc=last_msg)
                    last_msg = None
                continue

            text = message['text']
            author_id = message['user']
            author = self._get_author_details(author_id)
            if last_msg is not None:
                if last_msg.author == author.name:
                    last_msg.content += f"\n{text}"
                    continue
                else:
                    IndexQueue.get_instance().put_single(doc=last_msg)
                    last_msg = None

            timestamp = message['ts']
            message_id = message['client_msg_id']
            readable_timestamp = datetime.datetime.fromtimestamp(float(timestamp))
            message_url = f"https://slack.com/app_redirect?channel={conv.id}&message_ts={timestamp}"
            last_msg = BasicDocument(title=author.name, content=text, author=author.name,
                                     timestamp=readable_timestamp, id=message_id,
                                     data_source_id=self._data_source_id, location=conv.name,
                                     url=message_url, author_image_url=author.image_url,
                                     type=DocumentType.MESSAGE)

        if last_msg is not None:
            IndexQueue.get_instance().put_single(doc=last_msg)

    @retry(tries=5, delay=1, backoff=2, logger=logger)
    def _get_conversation_history(self, conv: SlackConversation, cursor: str, last_index_unix: str):
        try:
            return self._slack.conversations_history(channel=conv.id, oldest=last_index_unix,
                                                     limit=1000, cursor=cursor)
        except SlackApiError as e:
            logger.warning(f'SlackApi error while fetching messages for conversation {conv.name}: {e}')
            response = e.response
            if response['error'] == 'ratelimited':
                retry_after_seconds = int(response['headers']['Retry-After'])
                logger.warning(f'Rate-limited: Slack API rate limit exceeded,'
                               f' retrying after {retry_after_seconds} seconds')
                time.sleep(retry_after_seconds)
            raise e
        except IncompleteRead as e:
            logger.warning(f'IncompleteRead error while fetching messages for conversation {conv.name}')
            raise e

    def _fetch_conversation_messages(self, conv: SlackConversation):
        messages = []
        cursor = None
        has_more = True
        last_index_unix = self._last_index_time.timestamp()
        logger.info(f'Fetching messages for conversation {conv.name}')

        while has_more:
            try:
                response = self._get_conversation_history(conv=conv, cursor=cursor,
                                                          last_index_unix=str(last_index_unix))
            except Exception as e:
                logger.warning(f'Error fetching all messages for conversation {conv.name},'
                               f' returning {len(messages)} messages. Error: {e}')
                return messages

            logger.info(f'Fetched {len(response["messages"])} messages for conversation {conv.name}')
            messages.extend(response['messages'])
            if has_more := response["has_more"]:
                cursor = response["response_metadata"]["next_cursor"]

        return messages
