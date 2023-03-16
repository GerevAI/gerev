import logging
import os
import uuid
from typing import Optional

import posthog

from paths import UUID_PATH

logger = logging.getLogger(__name__)


class Posthog:
    API_KEY = "phc_unIQdP9MFUa5bQNIKy5ktoRCPWMPWgqTbRvZr4391Pm"
    HOST = 'https://eu.posthog.com'

    RUN_EVENT = "run"
    DAILY_EVENT = "daily"

    TEST_UUID = "test"
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
        if cls._identified_uuid is not None:
            logger.info(f"Skipping identify due to already identified UUID {cls._identified_uuid}")
            return

        if os.environ.get('TEST') == "1":
            cls._create_uuid_file(cls.TEST_UUID)
            cls._identified_uuid = cls.TEST_UUID
            logger.info("Identified as test UUID")
            return

        existing_uuid = cls._read_uuid_file()
        if cls.TEST_UUID in existing_uuid:
            cls._identified_uuid = cls.TEST_UUID
            logger.info("Identified as test UUID")
            return

        if existing_uuid is None:
            new_uuid = str(uuid.uuid4())
            logger.info(f"Generated new UUID: {new_uuid}")
            cls._create_uuid_file(new_uuid)
            cls._identified_uuid = new_uuid
        else:
            cls._identified_uuid = existing_uuid
            logger.info(f"Using existing UUID: {cls._identified_uuid}")

        try:
            posthog.identify(cls._identified_uuid)
        except Exception as e:
            logger.exception("Failed to identify posthog UUID")

    @classmethod
    def _capture(cls, event: str):
        if cls._identified_uuid is None:
            cls._identify()

        if cls._identified_uuid is None:
            logger.error(f"Failed to identify UUID, skipping event {event}")
            return

        if cls._identified_uuid == cls.TEST_UUID:
            logger.info(f"Skipping event {event} due to test UUID")
            return

        try:
            posthog.capture(cls._identified_uuid, event)
        except Exception as e:
            logger.error(f"Failed to send event {event} to posthog: {e}")

    @classmethod
    def send_daily(cls):
        cls._capture(cls.DAILY_EVENT)

    @classmethod
    def send_startup_telemetry(cls):
        cls._capture(cls.RUN_EVENT)
