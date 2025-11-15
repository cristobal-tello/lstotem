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

FIREBASE_FIELD_TYPES = [
    'null_value', 'boolean_value', 'integer_value', 'double_value', 'timestamp_value',
    'string_value', 'bytes_value', 'reference_value', 'geo_point_value', 
    'array_value', 'map_value'
]

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
                #json_string = raw.decode("utf-8", errors="ignore")
                #firestore_event_data: Dict[str, Any] = json.loads(json_string) 
                #fields = firestore_event_data.get('value', {}).get('fields', {})
                firestore_event = DocumentEventData.deserialize(raw)
                value: Document = firestore_event.value 
                resource_name = value.name

                fields = value.fields if value and value.fields else {}
                fields2 = _decode_firestore_fields(fields)
                
                logger.info("Firestore fields obtained from CloudEvent data.")
                logger.info(f"Resource name: {resource_name}")
                logger.info(f"Type of fields: {type(fields)}")
                logger.info(f"Type of fields: {type(fields2)}")
                logger.info(f"Data ': {fields2}")
                for key, value_obj in fields2.items():
                    logger.info(f"******** Key2: {key}, Value: {value_obj} *************")
                    
            else:
                # Local environment testing
                data = json.loads(json.dumps(raw))
                fields = data["value"]["fields"]
                logger.info("JSON")
                logger.info(f"Type of fields: {type(fields)}")

                for key, value_obj in fields.items():
                    # Extract the inner Firestore value (stringValue, doubleValue, integerValue, etc.)
                    inner_key = list(value_obj.keys())[0]
                    logger.info(f"******** Key: {key}, Value: {value_obj[inner_key]} *************")

        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
