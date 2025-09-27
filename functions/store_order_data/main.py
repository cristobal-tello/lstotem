import base64
import json
import logging
import re
from typing import Optional
from google.cloud import firestore

import functions_framework

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

try:
    # The client automatically uses FIRESTORE_EMULATOR_HOST if set locally
    # It uses production Firestore if the environment variable is unset (in GCP)
    db = firestore.Client()
    logger.info("Firestore client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")
    db = None # Set to None if initialization fails

@functions_framework.cloud_event
def store_order_data(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message (CloudEvent).
    """
    if db is None:
        logger.error("Skipping execution because Firestore client is not available.")
        # Return OK so the Pub/Sub message is not retried indefinitely
        return "Firestore Unavailable", 503
        
    try:
        message_id = cloud_event['id'] 
        
        logger.info("******** Start Processing *************")
        logger.info("Utilizando logger, CloudEvent ID: %s", message_id)

        raw = cloud_event.data

        if isinstance(raw, (bytes, bytearray)):
            text = raw.decode("utf-8", errors="ignore")
        elif isinstance(raw, str):
            text = raw
        else:
            text = json.dumps(raw)
        
        envelope = json.loads(text)
        
        # Extract and decode the base64 payload from the Pub/Sub envelope
        b64 = envelope["message"]["data"]
        if isinstance(b64, str):
            # Clean up base64 string (Pub/Sub message data is always a base64 string)
            b64 = re.sub(r"\s+", "", b64).encode("utf-8")
        
        message_data = base64.b64decode(b64).decode("utf-8")
        
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
        
        # Create a document reference using the order ID
        doc_ref = db.collection('orders').document(str(order_id))
        
        # Prepare the document to be saved
        document_data = {
            "orderId": order_id,
            "dateOrder": date_order,
            "totalOrder": total_order_num,
            "paymentType": payment_type,
            "deliveryType": delivery_type,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        
        # Save the data to Firestore
        doc_ref.set(document_data)
        logger.info(f"Successfully saved order {order_id} to Firestore.")
        
        # --- END FIRESTORE PERSISTENCE LOGIC ---
        
    except Exception:
        logger.exception("FATAL ERROR: Failed to process message") 
        return "Bad Request: Invalid message format", 400

    logger.info("Successfully processed request.")
    return "OK"