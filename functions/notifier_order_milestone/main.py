import logging
import firebase_admin

firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)

def notifier_order_milestone(event, context):
    """Triggered when a Firestore document is written in 'orders' collection."""
    logging.info(f"Triggered by Firestore event: {context.resource}")

    try:
        # 🔹 event ya es un dict; no decode
        logging.info(f"Raw event: {event}")

        # Accedemos al snapshot después del cambio
        value = event.get("value", {})
        fields = value.get("fields", {})

        if not fields:
            logging.warning("No 'fields' found in Firestore event. Skipping.")
            return

        logging.info(f"New document fields: {fields}")

        # Opcional: extraer ID de documento desde el resource
        resource = context.resource
        if resource and "documents/" in resource:
            order_id = resource.split("documents/")[-1]
            logging.info(f"🆔 Order document ID: {order_id}")

    except Exception as e:
        logging.error(f"Error processing Firestore event: {e}")
