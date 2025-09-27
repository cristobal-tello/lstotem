import base64
import json
import logging
import re
from typing import Optional
from rich.pretty import pprint
from rich import inspect

import functions_framework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.cloud_event
def store_order_data(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message (CloudEvent).
    Expects body like: {"message": {"data": "<base64(JSON order_data)>"}}.
    """
    try:
        logger.info("******** Start*************")
        # Normalize the envelope to a dict
        raw = cloud_event.data
        if isinstance(raw, (bytes, bytearray)):
            logger.info("pasa 22")
            text = raw.decode("utf-8", errors="ignore")
        elif isinstance(raw, str):
            logger.info("pasa 33")
            text = raw
        else:
            logger.info("pasa 44")
            text = json.dumps(raw)  # already a dict
        
        envelope = json.loads(text)
        b64 = envelope["message"]["data"]
        if isinstance(b64, str):
            b64 = re.sub(r"\s+", "", b64).encode("utf-8")  # strip newlines/whitespace
        message_data = base64.b64decode(b64).decode("utf-8")
        
        pprint(message_data, expand_all=True)
        order_data = json.loads(message_data)
        pprint(order_data, expand_all=True)

        pprint(order_data.get("orderId"))

        # Extract fields
        order_id = order_data.get("orderId")
        date_order = order_data.get("dateOrder")
        total_order = order_data.get("totalOrder")
        payment_type = order_data.get("paymentType")
        delivery_type = order_data.get("deliveryType")

        # Normalize totalOrder to a float if it comes as a string
        try:
            total_order_num = float(total_order) if total_order is not None else None
        except (TypeError, ValueError):
            total_order_num = None

        logger.info("Received order:")
        logger.info(f"  orderId      = {order_id}")
        logger.info(f"  dateOrder    = {date_order}")
        logger.info(f"  totalOrder   = {total_order} (parsed: {total_order_num})")
        logger.info(f"  paymentType  = {payment_type}")
        logger.info(f"  deliveryType = {delivery_type}")
        logger.info("******** END *************")

    except Exception:
        logger.exception("Error processing message")
        return "Bad Request: Invalid message format", 400

    logger.info("Successfully processed request.")
    return "OK"
