import datetime
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List

from pydantic import BaseModel
from rocketchat_API.rocketchat import RocketChat

from data_source_api.base_data_source import BaseDataSource, ConfigField, HTMLInputType
from data_source_api.basic_document import DocumentType, BasicDocument
from data_source_api.exception import InvalidDataSourceConfig
from indexing_queue import IndexingQueue


@dataclass
class RocketchatThread:
    id: str
    name: str
    channel_id: str


@dataclass
class RocketchatRoom:
    id: str
    name: str
    type: str
    archived: bool


@dataclass
class RocketchatAuthor:
    name: str
    image_url: str


class RocketchatConfig(BaseModel):
    url: str
    token_id: str
    token_secret: str


class RocketchatDataSource(BaseDataSource):
    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="Rockat.Chat instance URL", name="url"),
            ConfigField(label="User Token ID", name="token_id", type=HTMLInputType.PASSWORD),
            ConfigField(label="User Token Secret", name="token_secret", type=HTMLInputType.PASSWORD)
        ]

    @classmethod
    def get_display_name(cls) -> str:
        return "Rocket.Chat"

    @staticmethod
    def validate_config(config: Dict) -> None:
        rocket_chat_config = RocketchatConfig(**config)
        rocket_chat = RocketChat(user_id=rocket_chat_config.token_id, auth_token=rocket_chat_config.token_secret,
                                 server_url=rocket_chat_config.url)
        try:
            rocket_chat.me().json()
        except Exception as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        rocket_chat_config = RocketchatConfig(**self._config)
        self._rocket_chat = RocketChat(user_id=rocket_chat_config.token_id, auth_token=rocket_chat_config.token_secret,
                                       server_url=rocket_chat_config.url)
        self._authors_cache: Dict[str, RocketchatAuthor] = {}

    def _list_rooms(self, oldest: datetime) -> List[RocketchatRoom]:
        oldest = oldest.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        r = self._rocket_chat.call_api_get("rooms.get", updatedSince=oldest)
        json = r.json()
        data = json.get("update")

        rooms = []
        for r in data:
            room_id = r["_id"]
            if "fname" in r:
                name = r["fname"]
            elif "name" in r:
                name = r["name"]
            elif r["t"] == "d":
                my_uid = self._rocket_chat.me().json()["_id"]
                uid = next(filter(lambda u: u != my_uid, r["uids"]), None)
                if not uid:
                    uid = my_uid
                user = self._get_author_details(uid)
                name = user.name
            else:
                raise Exception("Unknown name")
            room_type = r["t"]
            archived = r.get("archived", False)
            rooms.append(RocketchatRoom(id=room_id, name=name, type=room_type, archived=archived))

        return rooms

    def _list_threads(self, channel: RocketchatRoom) -> List[RocketchatThread]:
        data = []
        records = 0
        total = 1  # Set 1 to enter the loop
        while records < total:
            r = self._rocket_chat.call_api_get("chat.getThreadsList", rid=channel.id, count=20, offset=records)
            json = r.json()
            data += json.get("threads")
            records = len(data)
            total = json.get("total")
        return [RocketchatThread(id=trds["_id"], name=trds["msg"], channel_id=trds["rid"]) for trds in data]

    def _list_messages(self, channel: RocketchatRoom, oldest: datetime):
        oldest = oldest.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = []
        while oldest:
            r = self._rocket_chat.call_api_get("chat.syncMessages", roomId=channel.id, lastUpdate=oldest)
            json = r.json()
            messages = json["result"].get("updated")
            if messages:
                data += messages
                oldest = messages[0]["_updatedAt"]
            else:
                oldest = None
        return data

    def _list_thread_messages(self, thread: RocketchatThread, oldest: datetime):
        oldest = oldest.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = []
        records = 0
        total = 1  # Set 1 to enter the loop
        while records < total:
            r = self._rocket_chat.call_api_get("chat.getThreadMessages", tmid=thread.id, tlm=oldest, count=20,
                                               offset=records)
            json = r.json()
            messages = json.get("messages")
            if messages:
                data += messages
            records = len(data)
            total = json.get("total")
        return data

    def _get_author_details(self, author_id: str) -> RocketchatAuthor:
        author = self._authors_cache.get(author_id, None)
        if author is None:
            author_info = self._rocket_chat.users_info(author_id).json().get("user")
            author = RocketchatAuthor(name=author_info.get("name", author_info.get("username")),
                                      image_url=f"{self._config.get('url')}/avatar/{author_info.get('username')}")
            self._authors_cache[author_id] = author

        return author

    def _feed_new_documents(self) -> None:
        documents = []
        for channel in self._list_rooms(self._last_index_time):
            last_msg: Optional[BasicDocument] = None

            messages = self._list_messages(channel, self._last_index_time)

            threads = self._list_threads(channel)
            for thread in threads:
                messages += self._list_thread_messages(thread, self._last_index_time)

            logging.info(f"Getting {len(messages)} messages from room {channel.name} ({channel.id})"
                         f" with {len(threads)} threads")

            for message in messages:
                if "msg" not in message:
                    continue
                text = message["msg"]
                author_id = message["u"]["_id"]
                author = self._get_author_details(author_id)

                if last_msg is not None:
                    if last_msg.author == author.name:
                        last_msg.content += f"\n{text}"
                        continue
                    else:
                        documents.append(last_msg)

                timestamp = message["ts"]
                message_id = message["_id"]
                readable_timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
                message_url = f"{self._config.get('url')}/{channel.id}?msg={message_id}"
                last_msg = BasicDocument(title=channel.name, content=text, author=author.name,
                                         timestamp=readable_timestamp, id=message_id,
                                         data_source_id=self._data_source_id, location=channel.name,
                                         url=message_url, author_image_url=author.image_url,
                                         type=DocumentType.MESSAGE)

            if last_msg is not None:
                documents.append(last_msg)

        logging.info(f"Total messages : {len(documents)}")
        IndexingQueue.get().feed(docs=documents)


if __name__ == "__main__":
    import os
    conf = {"url": os.environ["ROCKETCHAT_URL"], "token_id": os.environ["ROCKETCHAT_TOKEN_ID"], "token_secret": os.environ["ROCKETCHAT_TOKEN_SECRET"]}
    rc = RocketchatDataSource(config=conf, data_source_id=0)
    rc._feed_new_documents()
