import io
import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, List

from apiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from pydantic import BaseModel

from data_source.api.base_data_source import BaseDataSource, ConfigField, HTMLInputType, BaseDataSourceConfig
from data_source.api.basic_document import BasicDocument, DocumentType, FileType
from data_source.api.exception import KnownException
from parsers.docx import docx_to_html
from parsers.html import html_to_text
from parsers.pptx import pptx_to_text
from queues.index_queue import IndexQueue

logger = logging.getLogger(__name__)


class GoogleDriveConfig(BaseDataSourceConfig):
    json_str: str


class GoogleDriveDataSource(BaseDataSource):
    mime_type_to_parser = {
        'application/vnd.google-apps.document': html_to_text,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': lambda content: html_to_text(
            docx_to_html(content)),
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': pptx_to_text,
    }

    @staticmethod
    def get_config_fields() -> List[ConfigField]:
        return [
            ConfigField(label="JSON file content", name="json_str", input_type=HTMLInputType.TEXTAREA)
        ]

    @staticmethod
    def validate_config(config: Dict) -> None:
        try:
            scopes = ['https://www.googleapis.com/auth/drive.readonly']
            parsed_config = GoogleDriveConfig(**config)
            json_dict = json.loads(parsed_config.json_str)
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_dict, scopes=scopes)
            credentials.authorize(Http())
        except HttpError as e:
            raise KnownException(message="Drive token takes up to 10 minutes to get activated. "
                                         "Make sure you've followed *EVERY* step from the instructions "
                                         "& try again soon...")
        except (KeyError, ValueError) as e:
            raise KnownException(message="Invalid JSON file content")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        parsed_config = GoogleDriveConfig(**self._raw_config)
        json_dict = json.loads(parsed_config.json_str)
        self._credentials = ServiceAccountCredentials.from_json_keyfile_dict(json_dict, scopes=scopes)
        self._http_auth = self._credentials.authorize(Http())
        self._drive = build('drive', 'v3', http=self._http_auth)

        self._supported_mime_types = [
            'application/vnd.google-apps.document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]

    def _should_index_file(self, file):
        if file['mimeType'] not in self._supported_mime_types:
            logging.info(
                f"Skipping file {file['name']} because it's mime type is {file['mimeType']} which is not supported.")
            return False

        last_modified = datetime.strptime(file['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        if last_modified < self._last_index_time:
            return False

        return True

    @lru_cache(maxsize=512)
    def _get_parent_name(self, parent_id) -> dict:
        # The drive api returns just 'Drive' for the names of shared drives, so just skip it.
        try:
            result = self._drive.files().get(fileId=parent_id, fields='name,parents', supportsAllDrives=True).execute()
            if 'parents' in result and result['parents']:
                parent_name = self._get_parent_name(result['parents'][0])
                return parent_name + '/' + result['name'] if parent_name else result['name']
            else:
                return result['name'] if result['name'] != 'Drive' else ''
        except Exception as e:
            logging.exception(f"Error while getting folder name of id {id}")

    def _get_parents_string(self, file):
        return self._get_parent_name(file['parents'][0]) if file['parents'] else ''

    def _feed_new_documents(self) -> None:
        for drive in self._get_all_drives():
            self._feed_drive(drive=drive)

    def _feed_drive(self, drive):
        is_shared_drive = drive['id'] is not None
        logging.info(f'Indexing drive {drive["name"]}')

        kwargs = {
            'corpora': 'drive',
            'driveId': drive['id'],
            'includeItemsFromAllDrives': True,
            'supportsAllDrives': True,
        } if is_shared_drive else {}
        next_page_token = None
        while True:
            if next_page_token:
                kwargs['pageToken'] = next_page_token

            response = self._drive.files().list(
                fields='nextPageToken,files(kind,id,name,mimeType,lastModifyingUser,webViewLink,modifiedTime,parents,owners)',
                pageSize=1000,
                **kwargs
            ).execute()
            logger.info(f'got {len(response["files"])} documents from drive {drive["name"]}.')

            for file in response['files']:
                if self._should_index_file(file):
                    self._feed_file(file)

            next_page_token = response.get('nextPageToken')
            if next_page_token is None:
                break

    def _feed_file(self, file):
        logger.info(f'processing file {file["name"]}')

        file_id = file['id']
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
                    logger.error(f'Unsupported mime type {file["mimeType"]}')
                    return

                # delete file
                os.remove(file_to_download)
            except Exception as error:
                logging.exception(f'Error occurred parsing file "{file["name"]}" from google drive')

        parent_name = self._get_parents_string(file)

        last_modified = datetime.strptime(file['modifiedTime'], "%Y-%m-%dT%H:%M:%S.%fZ")

        author = file['lastModifyingUser'].get('displayName')
        author_image_url = file['lastModifyingUser'].get('photoLink')
        if not author:
            first_owner = file['owners'][0]
            author = first_owner.get('displayName')
            author_image_url = first_owner.get('photoLink')

        doc = BasicDocument(
            id=file_id,
            data_source_id=self._data_source_id,
            type=DocumentType.DOCUMENT,
            title=file['name'],
            content=content,
            author=author,
            author_image_url=author_image_url,
            location=parent_name,
            url=file['webViewLink'],
            timestamp=last_modified,
            file_type=FileType.from_mime_type(mime_type=file['mimeType']))
        IndexQueue.get_instance().put_single(doc)

    def _get_all_drives(self) -> List[dict]:
        return [{'name': 'My Drive', 'id': None}] \
            + self._drive.drives().list(fields='drives(id,name)').execute()['drives']
