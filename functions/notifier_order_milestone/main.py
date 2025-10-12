import json
import logging
import firebase_admin

firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


def notifier_order_milestone(event, context):
    """Triggered when a Firestore document is written in 'orders' collection."""
    logging.info(f"Triggered by Firestore event: {context.resource}")

    try:
        logging.info(f"Raw event: {event}")
        # Decode event bytes to dict if needed
        if isinstance(event, bytes):
            event = json.loads(event.decode("utf-8"))

        value = event.get("value", {})
        fields = value.get("fields", {})

        if not fields:
            logging.warning("No 'fields' found in Firestore event. Skipping.")
            return

        logging.info(f"New document fields: {fields}")

    except Exception as e:
        logging.error(f"Error processing Firestore event: {e}")
