# main.py para notifier_order_milestone

import logging
import firebase_admin
from datetime import datetime

# Importar las librerías necesarias del SDK de Firebase Functions y Admin
from firebase_functions import firestore_fn
from firebase_admin import firestore

# Inicializa Firebase Admin SDK
# Esto es necesario para que el SDK de Functions funcione correctamente.
firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


# La firma CORREGIDA DEBE ser solo (event) para Cloud Functions Gen 2 / Firebase SDK.
# El decorador se encarga de:
# 1. Asegurar la invocación con un solo argumento (resolviendo el TypeError).
# 2. Decodificar el payload binario de Firestore (resolviendo el AttributeError).
@firestore_fn.on_document_written(document="orders/{order_id}")
def notifier_order_milestone(event: firestore_fn.Event) -> None:
    """
    Se activa en la creación de un nuevo documento en la colección 'orders'.
    """
    
    # Verificamos si es un evento de creación:
    # `before.exists` es Falso en creación, `after.exists` es Verdadero.
    if not event.data.after.exists or event.data.before.exists:
        logging.info("Event was not a document creation (it was an update or delete). Skipping function execution.")
        return

    # Usar event.params para obtener el valor del wildcard {order_id} de la ruta.
    order_id = event.params["order_id"]
    logging.info(f"SUCCESS: Triggered by new document in 'orders' collection. ID: {order_id}")
    
    try:
        # event.data.after es el nuevo DocumentSnapshot, to_dict() decodifica los datos.
        new_order_data = event.data.after.to_dict()
        logging.info(f"Data for new order '{order_id}': {new_order_data}")

        # Aquí continuarías con la lógica de notificación (e.g., enviar a otro servicio).
        
    except Exception as e:
        logging.error(f"FATAL: Failed to extract data or process logic for document '{order_id}': {e}")