import os
import logging
import firebase_admin

# Import the necessary functions and types from the Firebase SDK
from firebase_functions import firestore_fn
from firebase_admin import firestore

# Initialize Firebase Admin SDK
firebase_admin.initialize_app() 
logging.basicConfig(level=logging.INFO)

# --- FIRESTORE CLIENT INITIALIZATION ---
# While not strictly needed for this logging function, we keep the client init pattern
# for environment clarity, but we remove the Pusher-specific environment checks.
emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

if emulator_host:
    logging.warning(f"DEV MODE: Firestore client connection configured for emulator at: {emulator_host}")
    
# Initialize the client (handles DEV/PROD switch implicitly via credentials)
# This client is currently unused but kept for potential future database interaction.
# db = firestore.client() 

# --- Function Trigger (Handles Create, Update, or Delete) ---
@firestore_fn.on_document_written(document="orders/{order_id}")
def notifier_order_milestone(event: firestore_fn.Event) -> None:
    """
    Triggers when an order document is inserted or updated. Logs the event type
    and document ID for auditing purposes.
    """
    # event.data is a Change object containing before and after snapshots
    change = event.data
    
    # 1. Extract Document ID and Determine Event Type
    doc_id = event.resource.split('/')[-1]

    # Check for document existence before and after the change
    doc_existed_before = change.before.exists
    doc_exists_after = change.after.exists

    event_type = "UNKNOWN"

    if not doc_existed_before and doc_exists_after:
        event_type = "INSERT (CREATED)"
    elif doc_existed_before and doc_exists_after:
        event_type = "UPDATE"
    elif doc_existed_before and not doc_exists_after:
        # This handles deletion, which we will log but is not strictly requested
        event_type = "DELETE"
    else:
        # Nothing happened (e.g., no data change, which can sometimes trigger a write)
        logging.info(f"Skipping write event with no detectable change for document: {doc_id}")
        return

    # 2. Log the Audit Event
    logging.info(f"==================================================")
    logging.info(f"AUDIT LOG: Firestore Event Detected: {event_type}")
    logging.info(f"Collection: orders | Document ID: {doc_id}")
    
    # 3. Log data summary for Created or Updated documents
    if doc_exists_after:
        try:
            data = change.after.to_dict()
            if data:
                logging.info(f"Document Data Summary: Keys={list(data.keys())}")
                # You can add more specific data logging here if needed
                # logging.info(f"Order Date: {data.get('dateOrder')}")
        except Exception as e:
            logging.warning(f"Could not extract document data for logging: {e}")

    logging.info(f"==================================================")

    # 4. NOTE: All Pusher and counting logic has been removed as requested.
