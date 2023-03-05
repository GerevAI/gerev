from datetime import datetime
from dataclasses import dataclass

class BasicDocument():
    id: int
    title: str
    content: str
    timestamp: datetime
    author: str

    # todo: this is temporary. needs to be automatically infered by the generating integration.
    integration_name: str