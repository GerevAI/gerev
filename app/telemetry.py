import os
import uuid
import posthog


def send_startup_telemetry():
    # Check if TEST environment variable is set
    if os.environ.get('TEST') == "1":
        # Write "test" to UUID file
        uuid_path = os.path.join(os.environ['HOME'], '.gerev.uuid')
        with open(uuid_path, 'w') as f:
            f.write("test")
        existing_uuid = "test"
        print("Using test UUID")
        return

    else:
        # Check if UUID file exists
        uuid_path = os.path.join(os.environ['HOME'], '.gerev.uuid')
        if os.path.exists(uuid_path):
            # Read existing UUID from file
            with open(uuid_path, 'r') as f:
                existing_uuid = f.read().strip()
            print(f"Using existing UUID: {existing_uuid}")
            # Check if UUID file contains "test"
            if "test" in existing_uuid:
                print("Skipping telemetry capture due to 'test' UUID")
                return
        else:
            # Generate a new UUID
            new_uuid = uuid.uuid4()
            print(f"Generated new UUID: {new_uuid}")
            # Write new UUID to file
            with open(uuid_path, 'w') as f:
                f.write(str(new_uuid))

            # Use the new UUID as the existing one
            existing_uuid = new_uuid

    # Capture an event with PostHog
    posthog.api_key = "phc_unIQdP9MFUa5bQNIKy5ktoRCPWMPWgqTbRvZr4391"
    posthog.host = 'https://eu.posthog.com'

    # Identify a user with the UUID
    posthog.identify(str(existing_uuid))

    # Capture an event
    posthog.capture(str(existing_uuid), "run")
