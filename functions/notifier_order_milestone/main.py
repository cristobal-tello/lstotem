# CÓDIGO CORREGIDO - Opción A: Usando Firebase Functions SDK
import logging
import firebase_admin

# Importar las funciones de Firebase Functions (necesitas estas importaciones)
from firebase_functions import firestore_fn

# Inicializa Firebase Admin SDK
firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


# La firma DEBE ser solo (event) para Cloud Functions Gen 2 / Firebase SDK
@firestore_fn.on_document_written(document="orders/{order_id}")
def notifier_order_milestone(event):
    """
    Triggers on new order creation and logs the data of the inserted document.
    """
    # NO se necesita importar ni usar 'context'

    # Usar las propiedades de DocumentSnapshot (event.data es un Change<DocumentSnapshot>)
    if not event.data.after.exists or event.data.before.exists:
        logging.info("Event was not a document creation or was an update/delete. Skipping.")
        return

    # Usar event.params para obtener el valor del wildcard {order_id}
    order_id = event.params["order_id"]
    logging.info(f"SUCCESS: Triggered by new document in 'orders' collection. ID: {order_id}")
    
    try:
        # Get the data from the newly created document snapshot
        new_order_data = event.data.after.to_dict()
        logging.info(f"Data for new order '{order_id}': {new_order_data}")
    except Exception as e:
        logging.error(f"Failed to extract data from new document '{order_id}': {e}")