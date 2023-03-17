import os
import uuid
from typing import Optional

import posthog

from paths import UUID_PATH


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

        return []

    @classmethod
    def _create_uuid_file(cls, user_uuid: str):
        with open(UUID_PATH, 'w') as f:
            f.write(user_uuid)

    @classmethod
    def send_startup_telemetry(cls):
        if cls._identified_uuid is not None:
            print("Skipping telemetry capture due to already identified UUID")
            return

        if os.environ.get('TEST') == "1":
            cls._create_uuid_file(cls.TEST_UUID)
            print("Skipping telemetry capture due to TEST=1")
            return

        existing_uuid = cls._read_uuid_file()
        if cls.TEST_UUID in existing_uuid:
            print("Skipping telemetry capture due to 'test' UUID")
            return

        if existing_uuid is None:
            new_uuid = str(uuid.uuid4())

            print(f"Generated new UUID: {new_uuid}")
            cls._create_uuid_file(new_uuid)

            existing_uuid = new_uuid

        # Identify a user with the UUID
        posthog.identify(existing_uuid)
        posthog.capture(existing_uuid, cls.RUN_EVENT)
        cls._identified_uuid = existing_uuid
