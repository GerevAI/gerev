import os
import io
import logging
from datetime import datetime
from typing import Dict

from apiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

from data_source_api.base_data_source import BaseDataSource
from data_source_api.basic_document import BasicDocument, DocumentType
from data_source_api.exception import InvalidDataSourceConfig
from indexing_queue import IndexingQueue
from parsers.html import html_to_text
from parsers.pptx import pptx_to_text
from parsers.docx import docx_to_html


class GoogleDriveDataSource(BaseDataSource):
    mime_type_to_parser = {
        'application/vnd.google-apps.document': html_to_text,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': lambda content: html_to_text(docx_to_html(content)),
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': pptx_to_text,
    }

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
        mime_types = [
            'application/vnd.google-apps.document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]
        return file['kind'] == 'drive#file' and file['mimeType'] in mime_types

    def _feed_new_documents(self) -> None:
        files = self._drive.files().list(fields='files(kind,id,name,mimeType,owners,webViewLink,modifiedTime,parents)').execute()
        files = files['files']
        files = [file for file in files if self._should_index_file(file)]
        documents = []

        logging.getLogger().info(f'got {len(files)} documents from google drive.')

        for file in files:
            logging.getLogger().info(f'processing file {file["name"]}')
            last_modified = datetime.strptime(file['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            if last_modified < self._last_index_time:
                continue

            file_id = file['id']
            file = self._drive.files().get(fileId=file_id,
                                           fields='id,name,mimeType,owners,webViewLink,modifiedTime,parents').execute()
            file_to_download = file['name']

            if file['mimeType'] == 'application/vnd.google-apps.document':
                content = self._drive.files().export(fileId=file_id, mimeType='text/html').execute().decode('utf-8')
                content = html_to_text(content)
            else:
                try:
                    request = self._drive.files().get_media(fileId=file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # write the downloaded content to a file
                    with open(file_to_download, 'wb') as f:
                        f.write(fh.getbuffer())

                    if file['mimeType'] == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
                        content = pptx_to_text(file_to_download)
                    elif file['mimeType'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        content = docx_to_html(file_to_download)
                        content = html_to_text(content)
                    else:
                        continue

                    # delete file
                    os.remove(file_to_download)
                except Exception as error:
                    print(f'An error occurred: {error}')

            try:
                parent = self._drive.files().get(fileId=file['parents'][0], fields='name').execute()
                parent_name = parent['name']
            except Exception as e:
                logging.exception(f"Error while getting folder name of google docs file {file['name']}")
                parent_name = ''

            documents.append(BasicDocument(
                id=file_id,
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
