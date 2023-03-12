from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class DocumentType(Enum):
    DOCUMENT = "document"
    MESSAGE = "message"
    COMMENT = "comment"
    PERSON = "person"


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

