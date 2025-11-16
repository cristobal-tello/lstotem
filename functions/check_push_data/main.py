import logging
import os # Import the os module to access environment variables
import inspect # To dynamically get the function name
import json
import base64
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
from google.events.cloud.firestore import DocumentEventData, Document
from google.events.cloud.firestore_v1.types.data import Value
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

def extract_value_from_proto(value_obj: Any) -> Any:
    """
    Safely extracts the primitive value from a proto Value object using getattr(),
    prioritizing non-zero/non-null fields to avoid the default 'null_value: 0' error.
    """
    
    # 1. Loop to find the actual set field
    for type_key in FIREBASE_FIELD_TYPES:
        
        if hasattr(value_obj, type_key):
            logger.info(f"Checking type_key: {type_key}")
            inner_value = getattr(value_obj, type_key)
            
            # --- CRITICAL FIX ---
            # If we hit 'null_value', we MUST skip it, otherwise we prematurely return 0.
            if type_key == 'null_value':
                logger.info(f"Skipping default null_value: {inner_value}")
                continue 
            
            # Check if the value is meaningfully set (non-None, non-empty, and not zero for numbers)
            # NOTE: We allow False for boolean_value and 0 for integer/double, but only if that's the only value set.
            # To be safe, we rely on the fact that only one field is populated.
            
            if inner_value is not None and inner_value != '':
                logger.info(f"Found set value for type_key {type_key}: {inner_value}")
                # If the value is a complex type (timestamp, map, array) or a string/boolean/number, we return it.
                return inner_value
                
    # 2. Fallback: If the loop finishes, the value must be NULL, 0, or False.
    # In this case, we rely on the object's representation of null, which is 'null_value'.
    if hasattr(value_obj, 'null_value'):
        logger.info(f"Falling back to null_value")
        # This will return 0, but it is the correct value for Firestore's NULL.
        return getattr(value_obj, 'null_value') 

    logger.warning("No valid value found in Value object.")
    return None

def unwrap_value(value_obj):
    # Check each known Firestore typed field
    if value_obj.string_value is not None:
        logger.info(f"Falling back to string_value: {value_obj.string_value}")
        return value_obj.string_value
    if value_obj.integer_value is not None:
        logger.info(f"Falling back to integer_value: {value_obj.integer_value}")
        return value_obj.integer_value
    if value_obj.double_value is not None:
        logger.info(f"Falling back to double_value: {value_obj.double_value}")
        return value_obj.double_value
    if value_obj.boolean_value is not None:
        logger.info(f"Falling back to boolean_value: {value_obj.boolean_value}")
        return value_obj.boolean_value
    if value_obj.timestamp_value is not None:
        logger.info(f"Falling back to timestamp_value: {value_obj.timestamp_value}")
        return value_obj.timestamp_value
    if value_obj.null_value is not None:
        logger.info(f"Falling back to null_value: {value_obj.null_value}")
        return None
    if value_obj.map_value is not None:
        logger.info(f"Falling back to map_value: {value_obj.map_value}")
        return None
    if value_obj.array_value is not None:
        logger.info(f"Falling back to array_value: {value_obj.array_value}")
        return [unwrap_value(v) for v in value_obj.array_value.values]

    return None  # fallback


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
                firestore_event = DocumentEventData.deserialize(raw)
                value: Document = firestore_event.value 
                resource_name = value.name

                firestore_fields = value.fields if value and value.fields else {}
                fields = _decode_firestore_fields(firestore_fields)
                
                logger.info(f"Resource name: {resource_name}")
                logger.info(f"Type of fields: {type(fields)}")
                logger.info(f"Data ': {fields}")
                for key, value_obj in fields.items():
                    logger.info(f"Type of value_obj: {type(value_obj)}")
                    logger.info(f"Dir of value_obj: {dir(value_obj)}")
                    if isinstance(value_obj, Value):
                        logger.info(f"******** Key2: {key}, Value: {value_obj}");
                        content = extract_value_from_proto(value_obj)
                        unwrap_value(value_obj)
                        logger.info(f"Extracted Value: {content}")
                    
            else:
                # Local environment testing
                data = json.loads(json.dumps(raw))
                resource_name = data["value"]["name"]
                fields = data["value"]["fields"]
                logger.info(f"Type of fields: {type(fields)}")

                for key, value_obj in fields.items():
                    if isinstance(value_obj, dict):
                        logger.info(f"Type of value_obj: {type(value_obj)}")
                        inner_key = list(value_obj.keys())[0]
                        logger.info(f"******** Key3: {key}, Value: {value_obj[inner_key]} *************")

        # logger.info("Final Resource name: %s", resource_name)
        # for key, value_obj in fields.items():
        #     logger.info(f"******** Final: {key}, Value: {value_obj} *************")
        
        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
