import logging
import firebase_admin
import json

firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


def notifier_order_milestone(event, context):
    """
    Cloud Function Gen 2 triggered on Firestore document writes.
    Supports new document creation, updates, and deletions.
    Works for Cloud Functions deployed with gcloud.
    """

    resource = getattr(context, "resource", None)
    logging.info(f"Triggered by Firestore event: {resource}")

    try:
        # -----------------------------
        # Normalize event to dict
        # -----------------------------
        if isinstance(event, bytes):
            try:
                event = json.loads(event.decode("utf-8"))
            except Exception:
                logging.warning("Event is bytes but could not decode as JSON; skipping.")
                return
        elif not isinstance(event, dict):
            logging.error(f"Unexpected event type: {type(event)}")
            return

        logging.info(f"Normalized event: {event}")

        # -----------------------------
        # Extract Firestore snapshots
        # -----------------------------
        value = event.get("value", {})      # After the change
        old_value = event.get("oldValue", {})  # Before the change

        # Detect document status
        if not old_value and value:
            status = "CREATED"
        elif old_value and value:
            status = "UPDATED"
        elif old_value and not value:
            status = "DELETED"
        else:
            status = "UNKNOWN"

        logging.info(f"Document status: {status}")

        # Extract fields from value (only if not deleted)
        fields = value.get("fields", {}) if value else {}
        if fields:
            logging.info(f"Document fields: {json.dumps(fields, indent=2)}")

        # Extract document ID from resource
        if resource and "documents/" in resource:
            doc_id = resource.split("documents/")[-1]
            logging.info(f"Document ID: {doc_id}")

    except Exception as e:
        logging.error(f"Error processing Firestore event: {e}")
