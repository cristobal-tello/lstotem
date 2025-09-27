import base64
import json
import logging
import re
from typing import Optional

import functions_framework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _decode_payload_from_envelope(envelope) -> Optional[dict]:
    """
    Returns the JSON-decoded payload dict contained in Pub/Sub message.data,
    or None on failure. Tolerates whitespace/newlines inside the base64.
    """
    # Case A: already a dict (best case)
    if isinstance(envelope, dict):
        msg = envelope.get("message", {})
        b64 = msg.get("data")
        if b64 is None:
            return None
        if isinstance(b64, str):
            b64_bytes = re.sub(r"\s+", "", b64).encode("utf-8")
        else:
            # bytes/bytearray
            b64_bytes = re.sub(rb"\s+", b"", b64)
        try:
            raw = base64.b64decode(b64_bytes, validate=False)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    # Case B: bytes or str -> try normal JSON first
    if isinstance(envelope, (bytes, bytearray)):
        text = envelope.decode("utf-8", errors="ignore")
    elif isinstance(envelope, str):
        text = envelope
    else:
        return None

    try:
        obj = json.loads(text)
        return _decode_payload_from_envelope(obj)  # recurse into Case A
    except json.JSONDecodeError:
        # JSON not parseable (likely due to raw newlines inside the "data" string)
        # Fallback: extract the base64 between "data":"...".
        m = re.search(r'"data"\s*:\s*"(?P<b64>.*?)"', text, flags=re.DOTALL)
        if not m:
            return None
        b64_str = m.group("b64")
        # Remove all whitespace/newlines that broke JSON
        b64_str = re.sub(r"\s+", "", b64_str)
        try:
            raw = base64.b64decode(b64_str.encode("utf-8"), validate=False)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

@functions_framework.cloud_event
def store_order_data(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message (CloudEvent).
    Expects body like: {"message": {"data": "<base64(JSON payload)>"}}.
    """
    try:
        payload = _decode_payload_from_envelope(cloud_event.data)
        if payload is None:
            logger.error("Could not decode payload from CloudEvent data.")
            return "Bad Request: Invalid message format", 400

        # Extract fields
        order_id = payload.get("orderId")
        date_order = payload.get("dateOrder")
        total_order = payload.get("totalOrder")
        payment_type = payload.get("paymentType")
        delivery_type = payload.get("deliveryType")

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

    except Exception:
        logger.exception("Error processing message")
        return "Bad Request: Invalid message format", 400

    logger.info("Successfully processed request.")
    return "OK"
