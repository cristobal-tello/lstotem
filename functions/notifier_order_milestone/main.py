import logging
import firebase_admin
import json

from google.events.cloud.firestore import v1 as firestoredata

firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


def notifier_order_milestone(event, context):
    """
    Cloud Function Gen 2 triggered on Firestore document writes.
    Decodes binary Firestore event payloads properly using google-events.
    """
    logging.info(f"Triggered by Firestore event: {getattr(context, 'resource', None)}")

    try:
        # Convert Firestore event bytes → FirestoreEvent object
        if isinstance(event, (bytes, bytearray)):
            firestore_event = firestoredata.DocumentEventData.deserialize(event)
        else:
            logging.warning(f"Unexpected event type {type(event)}; skipping.")
            return

        # Extract document snapshots
        value = firestore_event.value
        old_value = firestore_event.old_value

        if not old_value and value:
            status = "CREATED"
        elif old_value and value:
            status = "UPDATED"
        elif old_value and not value:
            status = "DELETED"
        else:
            status = "UNKNOWN"

        logging.info(f"Document status: {status}")

        # Extract document ID
        resource = getattr(context, "resource", "")
        doc_id = resource.split("documents/")[-1] if "documents/" in resource else None
        logging.info(f"Document ID: {doc_id}")

        # Log data if present
        if value and value.fields:
            logging.info(f"New document data: {json.dumps(value.fields, indent=2)}")

    except Exception as e:
        logging.error(f"Error processing Firestore event: {e}")
