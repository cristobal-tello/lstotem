import base64
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from google.cloud import firestore
import functions_framework

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Firestore client (lazy initialization)
_db = None

def get_firestore_client():
    """Initializes Firestore client if not already done."""
    global _db
    if _db is None:
        try:
            _db = firestore.Client()
            logger.info("Firestore client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    return _db


def _extract_pubsub_payload(ev):
    """Robustly extract the JSON payload from a Pub/Sub CloudEvent envelope.

    Accepts the functions-framework CloudEvent object or a plain dict.
    Returns the decoded JSON object of the inner Pub/Sub message.
    Raises ValueError for malformed or missing payloads.
    """
    # Get the raw event data (could be attribute or dict)
    if hasattr(ev, "data"):
        raw = ev.data
    elif isinstance(ev, dict):
        raw = ev.get("data") or ev
    else:
        raw = ev

    # Normalize to a JSON string
    if isinstance(raw, (bytes, bytearray)):
        text = raw.decode("utf-8", errors="ignore")
    elif isinstance(raw, str):
        text = raw
    else:
        text = json.dumps(raw)

    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("CloudEvent data is not valid JSON")

    # Try to find the base64 payload in common shapes
    message_b64 = None
    if isinstance(envelope, dict):
        message_b64 = envelope.get("message", {}).get("data")
        if not message_b64 and "data" in envelope and isinstance(envelope["data"], (str, bytes)):
            # Some runtimes place the base64 data directly under data
            message_b64 = envelope["data"]

    if not message_b64:
        raise ValueError("Pub/Sub envelope missing message.data")

    try:
        payload_text = base64.b64decode(message_b64).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to base64-decode message.data: {e}")

    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        raise ValueError("Message payload is not valid JSON")

@dataclass
class Order:
    """Represents the structure of an order."""
    dateOrder: str
    totalOrder: float
    paymentType: str
    deliveryType: str
    timestamp: object = firestore.SERVER_TIMESTAMP

    @classmethod
    def from_dict(cls, data: dict):
        """Creates an Order instance from a dictionary with validation."""
        try:
            return cls(
                dateOrder=data["dateOrder"],
                totalOrder=float(data["totalOrder"]),
                paymentType=data["paymentType"],
                deliveryType=data["deliveryType"],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Missing or invalid field in order data: {e}") from e

@functions_framework.cloud_event
def store_data(cloud_event):
    """
    Cloud Function triggered by a Pub/Sub message (CloudEvent).
    It parses order data and saves it to Firestore.
    """
    try:
        logger.info("******** Start Processing *************")
        logger.info("Processing CloudEvent ID: %s", cloud_event['id'])

        # Decode Pub/Sub message robustly
        order_payload = _extract_pubsub_payload(cloud_event)
        logger.info("Received order payload keys: %s", list(order_payload.keys()) if isinstance(order_payload, dict) else type(order_payload))

        # Validate and structure the data
        order = Order.from_dict(order_payload)

        # Save the validated order to Firestore
        client = get_firestore_client()
        doc_ref = client.collection('orders').document('LASTTIMESTAMP')
        doc_ref.set(asdict(order))

        # Log the full order content that was saved (safe-serialize any non-JSON types)
        logger.info("Order successfully saved. Order data: %s", json.dumps(asdict(order), default=str))

        logger.info("******** End Processing *************")

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to decode or parse Pub/Sub message: {e}")
        return "Bad Request: Invalid message format", 400
    except ValueError as e:
        logger.error(f"Failed during data validation: {e}")
        return "Bad Request: Invalid data payload", 400
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return "Internal Server Error", 500
