import os
import logging
from datetime import datetime
import firebase_admin

from firebase_functions import firestore_fn
from firebase_admin import firestore

firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)

emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

if emulator_host:
    logging.warning(f"DEV MODE: Firestore client connection configured for emulator at: {emulator_host}")

@firestore_fn.on_document_written(document="orders/{order_id}")
def notifier_order_milestone(event) -> None:
    """
    Triggers on new order creation and logs the data of the inserted document.
    """
    # We only care about new documents being created.
    # `before.exists` is False on creation, `after.exists` is True.
    if not event.data.after.exists or event.data.before.exists:
        logging.info("Event was not a document creation. Skipping function execution.")
        return

    order_id = event.params["order_id"]
    logging.info(f"SUCCESS: Triggered by new document in 'orders' collection. ID: {order_id}")
    
    try:
        new_order_data = event.data.after.to_dict()
        logging.info(f"Data for new order '{order_id}': {new_order_data}")
    except Exception as e:
        logging.error(f"Failed to extract data from new document '{order_id}': {e}")
