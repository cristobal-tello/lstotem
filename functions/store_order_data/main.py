import base64
import json
import logging
import re
from typing import Optional

import functions_framework

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

@functions_framework.cloud_event
def store_order_data(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message (CloudEvent).
    """
    try:
        message_id = cloud_event['id'] 
        
        # --- Using logger.info directly, removing pprint ---
        logger.info("Utilizando logger, CloudEvent ID: %s", message_id)
        
        logger.info("******** Start Processing *************")
        raw = cloud_event.data
        
        # This part of your code seems complex for standard Pub/Sub, but keeping logic:
        if isinstance(raw, (bytes, bytearray)):
            logger.info("pasa 22 (data is bytes)")
            text = raw.decode("utf-8", errors="ignore")
        elif isinstance(raw, str):
            logger.info("pasa 33 (data is str)")
            text = raw
        else:
            # Fallback for unexpected data format
            logger.info("pasa 44 (data is other type)")
            text = json.dumps(raw)
        
        envelope = json.loads(text)
        
        # Extract and decode the base64 payload from the Pub/Sub envelope
        b64 = envelope["message"]["data"]
        if isinstance(b64, str):
            # Clean up base64 string (Pub/Sub message data is always a base64 string)
            b64 = re.sub(r"\s+", "", b64).encode("utf-8")
        message_data = base64.b64decode(b64).decode("utf-8")
        
        # --- Using logger.info instead of pprint for message_data ---
        logger.info("Decoded Message Data: %s", message_data)

        order_data = json.loads(message_data)
        
        order_id = order_data.get("orderId")
        date_order = order_data.get("dateOrder")
        total_order = order_data.get("totalOrder")
        payment_type = order_data.get("paymentType")
        delivery_type = order_data.get("deliveryType")

        # Normalize totalOrder
        try:
            total_order_num = float(total_order) if total_order is not None else None
        except (TypeError, ValueError):
            total_order_num = None

        logger.info("Received order details:")
        logger.info(f"  orderId      = {order_id}")
        logger.info(f"  dateOrder    = {date_order}")
        logger.info(f"  totalOrder   = {total_order} (parsed: {total_order_num})")
        logger.info(f"  paymentType  = {payment_type}")
        logger.info(f"  deliveryType = {delivery_type}")
        logger.info("******** End Processing *************")

    except Exception:
        # logger.exception automatically captures the traceback for severe errors
        logger.exception("FATAL ERROR: Failed to process message") 
        return "Bad Request: Invalid message format", 400

    logger.info("Successfully processed request.")
    return "OK"