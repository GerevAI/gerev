# How to Add Your Own Data Source

## Setup development environment

Clone `gerev`
```bash
# clone with ssh
git clone git@github.com:GerevAI/gerev.git

# or clone with https
git clone https://github.com/GerevAI/gerev.git
```


Then setup backend:
```bash
cd gerev/app
pip install -r requirements.txt
uvicorn main:app
```

This will host UI on the same port too. [http://localhost:8000](http://localhost:80)

Wanna develop the UI? run:
```bash
cd ui
npm install
npm start
```
then go to [http://localhost:3000](http://localhost:3000)

<br>


---

## 0. Verify your data source is `Gerev-able`

Gerev supports data sources that are either:
1. Exposing a REST API.
2. Crawlable.
3. Accessible by the Gerev container some other way.


For instance, the Confluence data source uses the [Confluence REST API](https://developer.atlassian.com/cloud/confluence/rest/) to list spaces and then fetch Confluence pages ([atlassian-python-api](https://atlassian-python-api.readthedocs.io/))

The Slack data source uses the [Slack API](https://api.slack.com/) to list channels and then list messages from each channel ([slack_sdk](https://slack.dev/python-slack-sdk/))
<br>
<br>

### 0.1 **Rest API Tokens**

Find a way to generate some API key for your data source.

we'd recommend asking Google *"how to generate personal access token for \<your data source name>".*


Generating token usually involves going to your profile settings, creating a new access token, and copying it.


Got your token? Write down the process steps, you'll need it later.

<br>

---



## Let's go
This guide will walk you through the process of creating a data source for the imagniary website called `Magic`.

**Follow the steps below to create your custom data source:**



## 1. Create a package for your data source

1. Under `app/data_source/sources`, create a new `magic` python package with  `magic.py` and `__init__.py` files inside.


<br>

```
├── app
│   ├── data_source
│   │   ├── sources
│   │   │   ├── magic
│   │   │   │   ├── __init__.py
│   │   │   │   ├── magic.py
```

<br>

## 2. Import required modules
It's not common to guide you through the imports, but you'll need them all.

`magic.py`
```python
import logging
from datetime import datetime
from typing import List, Dict

from pydantic import BaseModel
from data_source.api.base_data_source import BaseDataSource, BaseDataSourceConfig, ConfigField
from data_source.api.basic_document import BasicDocument, DocumentType
from queues.index_queue import IndexQueue
```
<br>

## 3. Create a configuration class
Create a class that inherits from `BaseDataSourceConfig` for your data source configuration.

 Add your data-source's fields.

```python
class MagicConfig(BaseDataSourceConfig):
    url: str
    username: str
    token: str
```

<br>

## 4. Create a data source class
Create a new class that inherits from `BaseDataSource` and implement the 3 abstract methods:

4.1. `get_config_fields`

4.2. `validate_config`

4.3. `_feed_new_documents`

File structure:
```python
class MagicDataSource(BaseDataSource):

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        """
        list of the config fields which should be the same fields as in MagicConfig, for dynamic UI generation
        """
        pass

    @staticmethod
    async def validate_config(config: Dict) -> None:
        """
        Validate the configuration and raise an exception if it's invalid,
        You should try to actually connect to the data source and verify that it's working
        """
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        magic_config = MagicConfig(**self._config)
        self._magic_client = MagicClient(url=magic_config.url,
                                         username=magic_config.username,
                                         token=magic_config.token)

    def _feed_new_documents(self) -> None:
        """
        Add new documents to the index queue, will explaine later
        """
        pass
```

### 4.1. `get_config_fields`
Return a list of `ConfigField`s  that describes the data-source's configuration fields required (same fields as in `MagicConfig` but with UI fields).
```python
@staticmethod
def get_config_fields() -> List[ConfigField]:
    """
    list of the config fields which should be the same fields as in MagicConfig, for dynamic UI generation
    """
    return [
            ConfigField(label="URL", name="url", placeholder="Enter the URL of your Magic instance"),
            ConfigField(label="Username", name="username", placeholder="Enter your username"),
            ConfigField(label="Token", name="token", placeholder="Enter your token", input_type=HTMLInputType.PASSWORD)
        ]
```

### 4.2. `validate_config`
This method should validate the provided configuration and raise an InvalidDataSourceConfig exception if it's invalid.

it MUST connect to the data source and verify that it's working.

Some data-sources have a `auth_check` method, you can use it to verify the connection.
Otherwise you can try to list something from the data source.

```python
@staticmethod
async def validate_config(config: Dict) -> None:
        """
        Validate the configuration and raise an exception if it's invalid,
        You should try to actually connect to the data source and verify that it's working
        """
        try:
            parsed_config = MagicConfig(**config)
            magic_client = MagicClient(url=parsed_config.url,
                                       username=parsed_config.username,
                                       token=parsed_config.token)
            magic_client.auth_check() # if no such thing, try to list() something
        except Exception as e:
            raise InvalidDataSourceConfig from e
```

### 4.3. _feed_new_documents
This method should add new documents to the index queue. The implementation depends on the specific data source you're working with.

Flow should look like:

1. List spaces/channels/whatever from the data source.
2. Run tasks to fetch documents from each space/channel/whatever.
    * tasks are a built-in Gerev pipeline to run async functions with workers for maximum performance.
3. Parse each document into a `BasicDocument` object.
4. Feed the `BasicDocument` object to the index queue.
```python
def _feed_new_documents(self) -> None:
    channels = self._magic_client.list_channels()
    for channel in channels:
        self._add_task(self._feed_channel, channel)

def _fetch_channel(self, channel: Channel) -> None:
    messages = self._magic_client.list_messages(channel)
    for message in messages:
        doc = BasicDocument(
            id=message["id"],
            data_source_id=self._data_source_id,
            type=DocumentType.MESSAGE,
            title=message['title'],
            content=message.get("description"),
            author=message['author']['name'],
            author_image_url=message['author']['avatar_url'],
            location=message['references']['full'],
            url=message['web_url'],
            timestamp=message['created_at'],
        )
        IndexQueue.get_instance().put_single(document)
```
5. Before adding to queue, check whether document is newer than self._last_indexed_at, if not, skip it.
```python
last_modified = datetime.strptime(message["updated_at"], "%Y-%m-%dT%H:%M:%S.%f%z")
if last_modified < self._last_index_time:
    logger.info(f"Message {message['id']} is too old, skipping")
    continue
```

## 5. UI instructions

You should add your data source instructions to the UI.

### 5.1. data-source-panel.tsx
go to `gerev/ui/src/components/data-source-panel.tsx` and add your data source to the html.

```typescript
{
 this.state.selectedDataSource.value === 'Magic' && (
    <span className="flex flex-col leading-9  text-xl text-white">
       <span>1. {'Go to Magic -> top-right profile picture -> Edit profile'}</span>
       <span>2. {'Scroll down to API tokens -> Create token -> Name it'}</span>
       <span>3. {"Set 'Expiry Date' 01/01/2100, create, copy token id + token secret"}</span>
    </span>
 )
}
```


## 6. Logo 

Add your data-source logo.png to app/static/data_sources_icons.


Done! :rocket:

## Have any questions?

Join our 1000+ community members [Here!](https://discord.gg/6qZ2QZj)
