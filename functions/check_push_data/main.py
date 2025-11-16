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

def unwrap_value(value_obj):
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

    # if kind == "map_value":
    #     return unwrap_map(value_obj.map_value)

    if kind == "array_value":
        return [unwrap_value(v) for v in value_obj.array_value.values]

    return None

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
                for key, value_obj in fields.items():
                    if isinstance(value_obj, Value):
                        kind = value_obj._pb.WhichOneof("value_type")
                        content = unwrap_value(value_obj)
            else:
                # Local environment testing
                data = json.loads(json.dumps(raw))
                resource_name = data["value"]["name"]
                fields = data["value"]["fields"]

            logger.info("Resource name: %s", resource_name)
            for key, value_obj in fields.items():
                if isinstance(value_obj, dict):
                    inner_key = list(value_obj.keys())[0]
                    content = value_obj[inner_key]
                    
                if isinstance(value_obj, Value):
                    kind = value_obj._pb.WhichOneof("value_type")
                    content = unwrap_value(value_obj)
                
                logger.info(f"Field: {key}, Content: {content}")
        
        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
