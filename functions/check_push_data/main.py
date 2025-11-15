import logging
import os # Import the os module to access environment variables
import inspect # To dynamically get the function name
import json
import base64
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.events.cloud.firestore import DocumentEventData, Document
import functions_framework
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deserialize_firestore_fields(fields: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts Firestore's structured field format (e.g., {"fieldName": {"stringValue": "value"}}) 
    into a flat Python dictionary.
    """
    decoded_data = {}
    for key, firestore_type_value in fields.items():
        # The actual value is the first (and only) value in the inner dictionary.
        # This handles 'stringValue', 'doubleValue', 'integerValue', etc.
        if isinstance(firestore_type_value, dict) and firestore_type_value:
            # Get the value of the first item (e.g., the order ID, date, or total)
            decoded_data[key] = list(firestore_type_value.values())[0]
        else:
            decoded_data[key] = firestore_type_value
            
    return decoded_data

@functions_framework.cloud_event
def check_push_data(cloudevent):
    """
    Triggered by a Firestore event. Performs rate-limit check immediately.
    """
    try:
        func_name = inspect.currentframe().f_code.co_name
        logger.info(f"******** Start Processing: {func_name} *************")
        logger.info("Processing CloudEvent ID: %s", cloudevent['id'])

        # Get the raw event data (could be attribute or dict)
        if hasattr(cloudevent, "data"):
            raw = cloudevent.data

            if isinstance(raw, (bytes, bytearray)):
                # Google Cloud
                json_string = raw.decode("utf-8", errors="ignore")
                firestore_event_data: Dict[str, Any] = json.loads(json_string) 
                fields = firestore_event_data.get('value', {}).get('fields', {})
            elif isinstance(raw, str):
                logger.info("5")
                fields = raw
            else:
                # Local environment testing
                data = json.loads(json.dumps(raw))
                fields = data["value"]["fields"]
            
            logger.info(f"Fields: {fields}")
            
            result = {}

            for key, value_obj in fields.items():
                # Extract the inner Firestore value (stringValue, doubleValue, integerValue, etc.)
                inner_key = list(value_obj.keys())[0]
                result[key] = value_obj[inner_key]
                logger.info(f"******** Key: {key}, Value: {value_obj[inner_key]} *************")

       
       
       #data = deserialize_firestore_fields(payload)
       # logger.info(f"Deserialized Data: {data}")

         

        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
