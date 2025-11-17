import logging
import inspect # To dynamically get the function name
import json
import os
import random
from google.events.cloud.firestore import DocumentEventData, Document
from google.events.cloud.firestore_v1.types.data import Value
import functions_framework
import pusher
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_pusher_client = None

def _decode_firestore_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decodes Firestore structured fields from the DocumentEventData 
    into native Python types.
    """
    decoded_data = {}
    for key, firestore_type_value in fields.items():
        if isinstance(firestore_type_value, Value):
            # Handles live environment (Value protobuf objects)
            decoded_data[key] = unwrap_value(firestore_type_value)
        elif isinstance(firestore_type_value, dict) and firestore_type_value:
            # Handles local testing (JSON representation)
            # Assumes format like: {'stringValue': 'some_value'}
            value_type = list(firestore_type_value.keys())[0]
            decoded_data[key] = firestore_type_value[value_type]
        else:
            decoded_data[key] = firestore_type_value
    return decoded_data

def get_pusher_client():
    """Initializes and returns the Pusher client from environment variables."""
    global _pusher_client
    if _pusher_client is None:
        try:
            _pusher_client = pusher.Pusher(
                app_id=os.environ["PUSHER_APP_ID"],
                key=os.environ["PUSHER_APP_KEY"],
                secret=os.environ["PUSHER_APP_SECRET"],
                cluster=os.environ["PUSHER_CLUSTER"],
                ssl=True,
            )
            logger.info("Pusher client configuration: App ID=%s, Key=%s, Cluster=%s",
                        os.environ["PUSHER_APP_ID"],
                        os.environ["PUSHER_APP_KEY"],
                        os.environ["PUSHER_CLUSTER"])
            logger.info("Pusher client initialized successfully.")
        except KeyError as e:
            logger.error(f"Missing required Pusher environment variable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pusher client: {e}")
            raise
    return _pusher_client

def unwrap_value(value_obj: Value) -> Any:
    kind = value_obj._pb.WhichOneof("value_type")

    if kind == "string_value":
        return value_obj.string_value

    if kind == "double_value":
        return value_obj.double_value

    if kind == "integer_value":
        return value_obj.integer_value

    if kind == "boolean_value":
        return value_obj.boolean_value

    if kind == "null_value":
        return None

    if kind == "timestamp_value":
        return value_obj.timestamp_value

    if kind == "map_value":
        return {k: unwrap_value(v) for k, v in value_obj.map_value.fields.items()}

    if kind == "array_value":
        return [unwrap_value(v) for v in value_obj.array_value.values]

    return None

@functions_framework.cloud_event
def check_push_data(cloudevent):
    """Triggered by a Firestore event. Logs the data from the event."""
    try:
        func_name = inspect.currentframe().f_code.co_name
        logger.info(f"******** Start Processing: {func_name} *************")
        logger.info("Processing CloudEvent ID: %s", cloudevent['id'])

        resource_name: Optional[str] = None
        decoded_fields: Dict[str, Any] = {}

        raw_data = cloudevent.data

        if isinstance(raw_data, (bytes, bytearray)):
            # Live Google Cloud environment
            firestore_event = DocumentEventData.deserialize(raw_data)
            value: Optional[Document] = firestore_event.value
            if value:
                resource_name = value.name
                decoded_fields = _decode_firestore_fields(value.fields)
        elif isinstance(raw_data, dict):
            # Local testing environment
            value_data = raw_data.get("value", {})
            resource_name = value_data.get("name")
            firestore_fields = value_data.get("fields", {})
            decoded_fields = _decode_firestore_fields(firestore_fields)

        logger.info("Resource name: %s", resource_name)
        for key, content in decoded_fields.items():
            logger.info(f"Field: {key}, Content: {content}")

        # Generate a random number between 1 and 100 for rate-limiting simulation
        rate_limit_value= random.randint(1, 100)

        # --- Send Notification via Pusher ---
        pusher_client = get_pusher_client()

        payload = {'total': rate_limit_value}
        pusher_client.trigger(os.environ.get("PUSHER_CHANNEL"), os.environ.get("PUSHER_EVENT"), payload)
        logger.info(f"Successfully sent notification to Pusher on channel payload: {payload}")
        
        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
