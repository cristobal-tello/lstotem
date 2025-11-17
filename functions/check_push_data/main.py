import logging
import inspect # To dynamically get the function name
import json
import os
from datetime import datetime, timedelta, timezone
import random
from google.events.cloud.firestore import DocumentEventData, Document
from google.events.cloud.firestore_v1.types.data import Value
import functions_framework
import pusher
from typing import Dict, Any, Optional

from google.cloud import firestore
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global clients (lazy initialization)
_pusher_client = None


def get_push_threshold_minutes() -> int:
    """
    Gets the push threshold in minutes from the THRESHOLD_PUSH_DATA environment
    variable, defaulting to 3 if not found or invalid.
    """
    default_minutes = 3
    try:
        threshold_str = os.environ.get('THRESHOLD_PUSH_DATA')
        if threshold_str:
            # Convert to integer
            minutes = int(threshold_str)
            if minutes > 0:
                logger.info(f"Using configurable push threshold: {minutes} minutes.")
                return minutes
    except ValueError:
        logger.warning(
            f"Invalid value for THRESHOLD_PUSH_DATA environment variable. "
            f"Using default of {default_minutes} minutes."
        )
    logger.info(f"Using default push threshold: {default_minutes} minutes.")
    return default_minutes

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
            logger.info("Pusher client configuration: App ID=%s, Cluster=%s",
                        os.environ["PUSHER_APP_ID"],
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
    """
    Extracts the Python native value from a Firestore Value object using a
    dispatch pattern.
    """
    kind = value_obj._pb.WhichOneof("value_type")
    
    unwrap_map = {
        "string_value": lambda: value_obj.string_value,
        "double_value": lambda: value_obj.double_value,
        "integer_value": lambda: value_obj.integer_value,
        "boolean_value": lambda: value_obj.boolean_value,
        "null_value": lambda: None,
        "timestamp_value": lambda: value_obj.timestamp_value,
        "map_value": lambda: {k: unwrap_value(val) for k, val in value_obj.map_value.fields.items()},
        "array_value": lambda: [unwrap_value(val) for val in value_obj.array_value.values]
    }

    return unwrap_map.get(kind, lambda: None)()

def send_pusher_notification(count: int):
    """
    Sends a push notification via Pusher with the given payload.
    """
    pusher_client = get_pusher_client()
    payload = {'total': count}
    pusher_client.trigger(os.environ.get("PUSHER_CHANNEL"), os.environ.get("PUSHER_EVENT"), payload)
    logger.info(f"Successfully sent notification to Pusher on channel '{os.environ.get('PUSHER_CHANNEL')}' with payload: {payload}")

def _process_firestore_event_data(raw_data: Any) -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Processes raw CloudEvent data to extract resource name and decoded fields
    from a Firestore document event.
    Handles both live Google Cloud environment (bytes/bytearray) and local testing (dict).

    Returns:
        A tuple containing (resource_name, collection_path, decoded_fields).
    """
    resource_name: Optional[str] = None
    decoded_fields: Dict[str, Any] = {}

    if isinstance(raw_data, (bytes, bytearray)):
        firestore_event = DocumentEventData.deserialize(raw_data)
        value: Optional[Document] = firestore_event.value
        if value:
            resource_name = value.name
            decoded_fields = _decode_firestore_fields(value.fields)
    elif isinstance(raw_data, dict):
        value_data = raw_data.get("value", {})
        resource_name = value_data.get("name")
        firestore_fields = value_data.get("fields", {})
        decoded_fields = _decode_firestore_fields(firestore_fields)
    
    collection_path = None
    if resource_name:
        try:
            collection_path = resource_name.split('/documents/')[1].split('/')[0]
        except IndexError:
            logger.warning(f"Could not extract collection path from resource_name: {resource_name}")

    logger.info("Resource name: %s", resource_name)
    logger.info("Collection path: %s", collection_path)
    
    return resource_name, collection_path, decoded_fields

_db = None
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

def can_push_data(client, threshold_minutes: int) -> bool:
    """
    Checks if a push notification can be sent based on a rate-limiting mechanism.
    It reads the last push timestamp from Firestore and compares it against a threshold.

    Args:
        client: The Firestore client instance.
        threshold_minutes: The minimum number of minutes that must pass between pushes.

    Returns:
        True if a push can be sent (i.e., not rate-limited), False otherwise.
    """
    logger.info("Checking if push data can be sent based on threshold of %d minutes.", threshold_minutes)
    push_ref = client.collection('push').document('latest')
    latest_push_doc = push_ref.get()
    threshold_ago = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    if latest_push_doc.exists:
        last_timestamp = latest_push_doc.to_dict().get('lasttimestamp')
        logger.info("Threshold time (UTC): %s", threshold_ago)
        logger.info("Last push timestamp retrieved: %s", last_timestamp)
        if isinstance(last_timestamp, datetime) and last_timestamp > threshold_ago:
            logger.info(f"Skipping push.")
            return False
    
    return True

def _get_daily_document_count(client, collection_path: Optional[str]) -> int:
    """ 
    Queries Firestore for the count of documents created today in the
    specified collection.
    
    Args:
        client: The Firestore client instance.
        collection_path: The path of the collection to query.
        
    Returns:
        The total count of documents created today.
    """
    if collection_path:
        today = datetime.now(timezone.utc).date()
        # Query Firestore for documents created today in the specified collection
        aggregation_query = client.collection(collection_path).where(filter=firestore.FieldFilter('timestamp', '>=', datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc))).count()
        docs_today = aggregation_query.get()[0][0].value
        logger.info(f"Document count for collection '{collection_path}' today: {docs_today}")
        return docs_today 
    else:
        logger.warning(f"Could not determine collection path; it was not provided.")
        return 0 # Default to 0 if collection name cannot be determined


@functions_framework.cloud_event
def check_push_data(cloudevent):
    """Triggered by a Firestore event. Logs the data from the event."""
    try:
        func_name = inspect.currentframe().f_code.co_name
        logger.info(f"******** Start Processing: {func_name} *************")
        logger.info("Processing CloudEvent ID: %s", cloudevent['id'])

        client = get_firestore_client()

        threshold_minutes = get_push_threshold_minutes()
        if can_push_data(client, threshold_minutes):
            affected_table, collection_path, _ = _process_firestore_event_data(cloudevent.data)
            logger.info(f"Affected collection path: {collection_path}")
            logger.info(f"Affected resource name: {affected_table}")
            count = _get_daily_document_count(client, collection_path)
            send_pusher_notification(count)
            
            # Record the timestamp of this successful push to enforce rate limiting
            push_ref = client.collection('push').document('latest')
            push_ref.set({'lasttimestamp': firestore.SERVER_TIMESTAMP})
        
        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
