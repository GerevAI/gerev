from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    DOCUMENT = "document"
    MESSAGE = "message"
    COMMENT = "comment"
    PERSON = "person"


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
    id: int
    data_source_id: int
    type: DocumentType
    title: str
    content: str
    timestamp: datetime
    author: str
    author_image_url: str
    location: str
    url: str
    file_type: FileType = None

