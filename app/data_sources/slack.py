import datetime
from dataclasses import dataclass
from typing import Optional, Dict, List

from pydantic import BaseModel
from slack_sdk import WebClient

from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.basic_document import DocumentType, BasicDocument
from indexing_queue import IndexingQueue


@dataclass
class SlackConversation:
    id: str
    name: str


@dataclass
class SlackAuthor:
    name: str
    image_url: str


class SlackConfig(BaseModel):
    token: str


class SlackDataSource(BaseDataSource):

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
        slack_config = SlackConfig(**self._config)
        self._slack = WebClient(token=slack_config.token)
        self._authors_cache: Dict[str, SlackAuthor] = {}

    def _list_conversations(self) -> List[SlackConversation]:
        conversations = self._slack.conversations_list(exclude_archived=True)
        return [SlackConversation(id=conv['id'], name=conv['name'])
                for conv in conversations['channels']]

    def _join_conversations(self, conversations: List[SlackConversation]):
        for conv in conversations:
            self._slack.conversations_join(channel=conv.id)

    def _get_author_details(self, author_id: str) -> SlackAuthor:
        author = self._authors_cache.get(author_id, None)
        if author is None:
            author_info = self._slack.users_info(user=author_id)
            author = SlackAuthor(name=author_info['user']['real_name'],
                                 image_url=author_info['user']['profile']['image_72'])
            self._authors_cache[author_id] = author

        return author

    def _feed_new_documents(self) -> None:
        conversations = self._list_conversations()
        self._join_conversations(conversations)

        last_index_unix = self._last_index_time.timestamp()
        documents = []
        for conv in conversations:
            last_msg: Optional[BasicDocument] = None

            messages = []
            has_more = True
            cursor = None
            while has_more:
                response = self._slack.conversations_history(channel=conv.id, oldest=str(last_index_unix),
                                                             limit=1000, cursor=cursor)
                messages.extend(response['messages'])
                if has_more := response["has_more"]:
                    cursor = response["response_metadata"]["next_cursor"]

            for message in messages:
                if not self._is_valid_message(message):
                    if last_msg is not None:
                        documents.append(last_msg)
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
                        documents.append(last_msg)

                timestamp = message['ts']
                message_id = message['client_msg_id']
                readable_timestamp = datetime.datetime.fromtimestamp(float(timestamp))
                message_url = f"https://slack.com/app_redirect?channel={conv.id}&message_ts={timestamp}"
                last_msg = BasicDocument(title=conv.name, content=text, author=author.name,
                                         timestamp=readable_timestamp, id=message_id,
                                         data_source_id=self._data_source_id, location=conv.name,
                                         url=message_url, author_image_url=author.image_url,
                                         type=DocumentType.MESSAGE)

            if last_msg is not None:
                documents.append(last_msg)

        IndexingQueue.get().feed(docs=documents)
