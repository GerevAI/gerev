import datetime
import os
from dataclasses import dataclass
from typing import Optional, Dict, List

from slack_sdk import WebClient

from data_sources.data_source import DataSource
from integrations_api import BasicDocument
from integrations_api.basic_document import ResultType


@dataclass
class SlackConversation:
    id: str
    name: str


class SlackDataSource(DataSource):

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        # TODO: add validation
        self._slack = WebClient(token=os.getenv('SLACK_TOKEN'))
        self._authors_cache = {}

    @staticmethod
    def _is_message(message: Dict) -> bool:
        return 'client_msg_id' in message

    def _list_conversations(self) -> List[SlackConversation]:
        conversations = self._slack.conversations_list()
        return [SlackConversation(id=conv['id'], name=conv['name'])
                for conv in conversations['channels']]

    def _join_conversations(self, conversations: List[SlackConversation]):
        for conv in conversations:
            self._slack.conversations_join(channel=conv.id)

    def _get_author_name(self, author_id: str) -> str:
        author_name = self._authors_cache.get(author_id)
        if author_name is None:
            author_name = self._slack.users_info(user=author_id)['user']['real_name']
            self._authors_cache[author_id] = author_name

        return author_name

    def get_documents(self) -> List[BasicDocument]:
        conversations = self._list_conversations()
        self._join_conversations(conversations)

        documents = []
        for conv in conversations:
            last_msg: Optional[BasicDocument] = None
            messages = self._slack.conversations_history(channel=conv.id)
            for message in messages['messages']:
                if not self._is_message(message):
                    continue

                text = message['text']
                author_id = message['user']
                author_name = self._get_author_name(author_id)
                if last_msg is not None:
                    if last_msg.author == author_name:
                        last_msg.content += f"\n{text}"
                        continue
                    else:
                        documents.append(last_msg)

                timestamp = message['ts']
                message_id = message['client_msg_id']
                readable_timestamp = datetime.datetime.fromtimestamp(float(timestamp))
                url = f"https://slack.com/app_redirect?channel={conv.id}&message_ts={timestamp}"
                last_msg = BasicDocument(title=conv.name, content=text, author=author_name,
                                         timestamp=readable_timestamp, id=message_id,
                                         integration_name='slack', location=conv.name,
                                         url=url, type=ResultType.MESSAGE)

        if last_msg is not None:
            documents.append(last_msg)

        return documents


if __name__ == '__main__':
    print(SlackDataSource().get_documents())
