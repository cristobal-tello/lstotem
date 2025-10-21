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

@dataclass
class Order:
    """Represents the structure of an order."""
    orderId: str
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
                orderId=str(data["orderId"]),
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

        # 0. Initialize client and check if the last order was processed recently
        client = get_firestore_client()
        query = client.collection('orders').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1)
        results = list(query.stream())
        if results:
            last_order = results[0].to_dict()
            last_timestamp = last_order.get('timestamp')

            # Firestore timestamps are timezone-aware (UTC). Compare with current UTC time.
            two_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=2)

            # If the last order is more recent than two minutes ago, log it and continue.
            if last_timestamp > two_minutes_ago:
                logger.info("A recent order was processed at %s (within the last 2 minutes). Continuing with current order.", last_timestamp)


        # 1. Decode Pub/Sub message
        order_payload = json.loads(base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8"))
        logger.info("Received order payload: %s", order_payload)

        # 2. Validate and structure the data
        order = Order.from_dict(order_payload)

        # 3. Save the validated order to Firestore
        doc_ref = client.collection('orders').document(order.orderId)
        doc_ref.set(asdict(order))

        logger.info("Order %s successfully saved. ******** End Processing *************", order.orderId)

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to decode or parse Pub/Sub message: {e}")
        return "Bad Request: Invalid message format", 400
    except ValueError as e:
        logger.error(f"Failed during data validation: {e}")
        return "Bad Request: Invalid data payload", 400
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return "Internal Server Error", 500
