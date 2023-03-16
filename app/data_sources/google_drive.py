import logging
from typing import Optional, Dict
from datetime import datetime

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http

from indexing_queue import IndexingQueue
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.base_data_source import BaseDataSource
from data_source_api.exception import InvalidDataSourceConfig
from parsers.html import html_to_text


class GoogleDriveDataSource(BaseDataSource):
    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            scopes = ['https://www.googleapis.com/auth/drive.readonly']
            ServiceAccountCredentials.from_json_keyfile_dict(config, scopes=scopes)
        except (KeyError, ValueError) as e:
            raise InvalidDataSourceConfig from e

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Create a google cloud project in https://console.cloud.google.com/projectcreate
        # select the project you created and add service account in https://console.cloud.google.com/iam-admin/serviceaccounts
        # create an api key for the service account and download it
        # share the google drive folder with the service account email address.
        # put the contents of the downloaded file in the config
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        self._credentials = ServiceAccountCredentials.from_json_keyfile_dict(self._config, scopes=scopes)
        self._http_auth = self._credentials.authorize(Http())
        self._drive = build('drive', 'v3', http=self._http_auth)

    def _should_index_file(self, file):
        return file['kind'] == 'drive#file' and file['mimeType'] == 'application/vnd.google-apps.document'

    def _feed_new_documents(self) -> None:
        files = self._drive.files().list(fields='files(kind,id,name,mimeType,owners,webViewLink,modifiedTime,parents)').execute()
        files = files['files']
        files = [file for file in files if self._should_index_file(file)]
        documents = []

        logging.getLogger().info(f'got {len(files)} documents from google drive.')

        for file in files:
            last_modified =  datetime.strptime(file['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue
            id = file['id']
            content = self._drive.files().export(fileId=id, mimeType='text/html').execute().decode('utf-8')
            content = html_to_text(content)
            try:
                parent = self._drive.files().get(fileId=file['parents'][0], fields='name').execute()
                parent_name = parent['name']
            except Exception as e:
                logging.exception(f"Error while getting folder name of google docs file {file['name']}")
                parent_name = ''

            documents.append(BasicDocument(
                id=id,
                data_source_id=self._data_source_id,
                type=DocumentType.DOCUMENT,
                title=file['name'],
                content=content,
                author=file['owners'][0]['displayName'],
                author_image_url=file['owners'][0]['photoLink'],
                location=parent_name,
                url=file['webViewLink'],
                timestamp=last_modified
            ))

        IndexingQueue.get().feed(documents)
