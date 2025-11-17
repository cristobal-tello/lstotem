import logging
import inspect # To dynamically get the function name
import json
import os
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.events.cloud.firestore import DocumentEventData, Document
from google.events.cloud.firestore_v1.types.data import Value
import functions_framework
import pusher
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients (lazy initialization)
_db = None
_pusher_client = None

def get_firestore_client():
    """Initializes and returns the Firestore client."""
    global _db
    if _db is None:
        try:
            _db = firestore.Client()
            logger.info("Firestore client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    return _db

def get_pusher_client():
    """Initializes and returns the Pusher client from environment variables."""
    global _pusher_client
    if _pusher_client is None:
        try:
            _pusher_client = pusher.Pusher(
                app_id=os.environ["PUSHER_APP_ID"],
                key=os.environ["PUSHER_KEY"],
                secret=os.environ["PUSHER_SECRET"],
                cluster=os.environ["PUSHER_CLUSTER"],
                ssl=True,
            )
            logger.info("Pusher client initialized successfully.")
        except KeyError as e:
            logger.error(f"Missing required Pusher environment variable: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Pusher client: {e}")
            raise
    return _pusher_client

def _get_document_id_from_name(resource_name: str) -> Optional[str]:
    """Safely extracts the document ID from the Firestore resource name string."""
    try:
        return resource_name.split("/documents/")[1].split("/")[-1]
    except (IndexError, AttributeError):
        logger.error(f"Could not parse document ID from resource: {resource_name}")
        return None

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
    """
    Triggered by a Firestore document creation. Performs a rate-limit check
    and sends a push notification via Pusher with the new document's data.
    """
    try:
        func_name = inspect.currentframe().f_code.co_name
        logger.info(f"******** Start Processing: {func_name} *************")
        logger.info("Processing CloudEvent ID: %s", cloudevent['id'])

        client = get_firestore_client()
        
        # # For this example, we'll assume a simple 1-minute rate limit.
        # # You can make this configurable as shown in your futurecode.py.
        # threshold_minutes = 1
        # push_ref = client.collection('push').document('latest')
        # latest_push_doc = push_ref.get()
        # threshold_ago = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        # if latest_push_doc.exists:
        #     last_timestamp = latest_push_doc.to_dict().get('lasttimestamp')
        #     if isinstance(last_timestamp, datetime) and last_timestamp > threshold_ago:
        #         logger.warning(
        #             f"Skipping push. Last push at {last_timestamp} is within the "
        #             f"{threshold_minutes}-minute threshold."
        #         )
        #         return "OK, rate-limited", 200 # Acknowledge and exit early

        # Deserialize the event data
        firestore_event = DocumentEventData.deserialize(cloudevent.data)
        value: Optional[Document] = firestore_event.value
        old_value: Optional[Document] = firestore_event.old_value

        # We only care about new documents, not updates or deletes
        if not value or old_value:
            logger.info("Event was not a document creation. Skipping.")
            return "OK, not a create event", 200

        resource_name = value.name
        order_id = _get_document_id_from_name(resource_name)

        # Ensure the event is for the 'orders' collection
        if not order_id or 'orders' not in resource_name:
            logger.error(f"Invalid resource or not an 'orders' document: {resource_name}")
            return "Invalid Resource", 400
        
        logger.info(f"SUCCESS: Triggered by new order document. ID: {order_id}")
        new_order_data = _decode_firestore_fields(value.fields)
        logger.info(f"Data for new order '{order_id}': {new_order_data}")

        # --- Send Notification via Pusher ---
        pusher_client = get_pusher_client()
        pusher_client.trigger('orders', 'new-order', {'id': order_id, 'data': new_order_data})
        logger.info(f"Successfully sent notification for order '{order_id}' to Pusher.")

        # Record the timestamp of this successful push to enforce rate limiting
       # push_ref.set({'lasttimestamp': firestore.SERVER_TIMESTAMP})

        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
