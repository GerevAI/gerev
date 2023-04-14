from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Union, List


class DocumentType(Enum):
    DOCUMENT = "document"
    MESSAGE = "message"
    COMMENT = "comment"
    PERSON = "person"
    ISSUE = "issue"
    GIT_PR = "git_pr"


class DocumentStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class FileType(Enum):
    GOOGLE_DOC = "doc"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"

    @classmethod
    def from_mime_type(cls, mime_type: str):
        if mime_type == 'application/vnd.google-apps.document':
            return cls.GOOGLE_DOC
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return cls.DOCX
        elif mime_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
            return cls.PPTX
        elif mime_type == 'text/plain':
            return cls.TXT
        else:
            return None


@dataclass
class BasicDocument:
    id: Union[int, str]  # row id in database
    data_source_id: int  # data source id in database
    type: DocumentType
    title: str
    content: str
    timestamp: datetime
    author: str
    author_image_url: str
    location: str
    url: str
    status: str = None
    is_active: bool = None
    file_type: FileType = None
    children: List['BasicDocument'] = None

    @property
    def id_in_data_source(self):
        return str(self.data_source_id) + '_' + str(self.id)

