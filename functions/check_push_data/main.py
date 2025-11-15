import logging
import functions_framework
import os # Import the os module to access environment variables
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.events.cloud.firestore import DocumentEventData, Document
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Firestore client (lazy initialization)
_db = None

def get_push_threshold_minutes() -> int:
    """
    Gets the push threshold in minutes from the THRESHOLD_PUSH_DATA environment
    variable, defaulting to 5 if not found or invalid.
    """
    default_minutes = 5
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

def _decode_firestore_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decodes Firestore structured fields from the DocumentEventData 
    into native Python types.
    """
    decoded_data = {}
    for key, firestore_type_value in fields.items():
        if isinstance(firestore_type_value, dict) and firestore_type_value:
            decoded_data[key] = list(firestore_type_value.values())[0]
        else:
            decoded_data[key] = firestore_type_value
    return decoded_data

def _get_document_id_from_name(resource_name: str) -> str:
    """Safely extracts the document ID from the Firestore resource name string."""
    try:
        path = resource_name.split("/documents/")[1]
        doc_id = path.split("/")[-1]
        return doc_id
    except (IndexError, AttributeError):
        logger.error(f"Could not parse document ID from resource: {resource_name}")
        return None

@functions_framework.cloud_event
def check_push_data(cloudevent):
    """
    Triggered by a Firestore event. Performs rate-limit check immediately.
    """
    try:
        logger.info("******** Start Processing: check_push_data *************")
        logger.info("Processing CloudEvent ID: %s", cloudevent.get('id'))

        client = get_firestore_client()
        
        # Rate Limiting Check ---
        
        threshold_minutes = get_push_threshold_minutes()

        push_ref = client.collection('push').document('latest')
        latest_push_doc = push_ref.get()

        threshold_ago = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        if latest_push_doc.exists:
            last_timestamp = latest_push_doc.to_dict().get('lasttimestamp')

            if isinstance(last_timestamp, datetime) and last_timestamp > threshold_ago:
                logger.warning(
                    f"Skipping push. Last push at {last_timestamp} is within the "
                    f"{threshold_minutes}-minute threshold."
                )
                return "OK", 200 # Acknowledge and exit early
        
        logger.info("Rate limit check passed. Proceeding with event processing.")
        
        #  Event Processing

        # Deserialize the event data only after the rate limit check passes
        firestore_event = DocumentEventData.deserialize(cloudevent.data) 
        value: Document = firestore_event.value 
        old_value: Document = firestore_event.old_value
        
        if not value or old_value: 
            logger.info("Event was not a document creation or value is missing. Skipping.")
            return "OK", 200

        # Get the collection and document ID
        resource_name = value.name
        order_id = _get_document_id_from_name(resource_name)
        
        # BASIC VALIDATION: Ensure the event is for the expected 'orders' collection
        if not order_id or 'orders' not in resource_name:
            logger.error(f"Invalid resource name or not an 'orders' document: {resource_name}")
            return "Invalid Resource Format", 400
        
        logger.info(f"SUCCESS: Triggered by new order document. ID: {order_id}")
        
        # Extract and decode the new order data
        fields = value.fields if value and value.fields else {}
        new_order_data = _decode_firestore_fields(fields)

        logger.info(f"Data for new order '{order_id}': {new_order_data}")

        # --- Add your push notification logic here ---
        logger.info("--> PUSHER SEND NOTIFICATION HERE <---")
        
        # Record the timestamp of this successful push event
        push_ref.set({'lasttimestamp': firestore.SERVER_TIMESTAMP})
        
        logger.info("******** End Processing: check_push_data *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500