import logging
import os
from typing import Optional
from uuid import uuid4

import posthog

from paths import UUID_PATH

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s')
logger = logging.getLogger(__name__)


class Posthog:
    API_KEY = "phc_unIQdP9MFUa5bQNIKy5ktoRCPWMPWgqTbRvZr4391Pm"
    HOST = 'https://eu.posthog.com'

    RUN_EVENT = "run"
    BACKEND_SEARCH_EVENT = "backend_search"
    _should_capture = False
    _identified_uuid: Optional[str] = None

    @classmethod
    def _read_uuid_file(cls) -> Optional[str]:
        if os.path.exists(UUID_PATH):
            with open(UUID_PATH, 'r') as f:
                existing_uuid = f.read().strip()
                return existing_uuid

        return None

    @classmethod
    def _create_uuid_file(cls, user_uuid: str):
        with open(UUID_PATH, 'w') as f:
            f.write(user_uuid)

    @classmethod
    def _identify(cls):
        if not os.environ.get('CAPTURE_TELEMETRY'):
            return

        cls._should_capture = True

        user_uuid = cls._read_uuid_file()
        if user_uuid is None:
            new_uuid = str(uuid4())
            cls._create_uuid_file(new_uuid)
            user_uuid = new_uuid

        try:
            posthog.api_key = cls.API_KEY
            posthog.host = cls.HOST
            posthog.identify(user_uuid)
            cls._identified_uuid = user_uuid
        except Exception as e:
            pass

    @classmethod
    def _capture(cls, event: str, uuid=None):
        if cls._identified_uuid is None:
            cls._identify()

        if not cls._should_capture:
            return

        try:
            posthog.capture(uuid or cls._identified_uuid, event)
        except Exception as e:
            pass

    @classmethod
    def send_daily(cls):
        cls._capture(cls.RUN_EVENT)

    @classmethod
    def send_startup_telemetry(cls):
        cls._capture(cls.RUN_EVENT)

    @classmethod
    def increase_search_count(cls, uuid: str):
        cls._capture(cls.BACKEND_SEARCH_EVENT, uuid=uuid)
