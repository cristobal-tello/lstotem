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
            logger.info("1")
            raw = cloudevent.data
            
        elif isinstance(cloudevent, dict):
            logger.info("2")
            raw = cloudevent.get("data") or cloudevent
        else:
            logger.info("3")
            raw = cloudevent

        if isinstance(raw, (bytes, bytearray)):
            logger.info("4")
            firestore_event = DocumentEventData.deserialize(cloudevent.data) 
            text: Document = firestore_event.value 
        elif isinstance(raw, str):
            logger.info("5")
            text = raw
        else:
            logger.info("6")
            text = json.dumps(raw)
        
        logger.info(f"{text}")

        logger.info(f"******** End Processing: {func_name} *************")
        return "OK", 200
    
    except Exception as e:
        logger.exception("Unexpected error in check_push_data: %s", e)
        return "Internal Server Error", 500
