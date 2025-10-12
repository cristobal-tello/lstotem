# notifier_order_milestone.py

import logging
import firebase_admin

# Importar las librerías necesarias
from google.cloud import firestore
import functions_framework # <--- ¡Asegúrate de que esta línea esté presente!

# La librería firestore_fn ya no es necesaria, la eliminamos si solo tienes esto
# from firebase_functions import firestore_fn 
from firebase_functions import firestore_fn # (Si la mantienes, no hace daño, pero es redundante)


# Inicializa Firebase Admin SDK
firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)


# CAMBIO CLAVE: Usamos el decorador estándar de CloudEvent de functions-framework
@functions_framework.cloud_event
def notifier_order_milestone(cloudevent): # <--- Usamos el nombre 'cloudevent' por convención
    """
    Triggers on new order creation and logs the data of the inserted document.
    """
    # El evento real de Firestore está anidado en cloudevent.data
    event_data = cloudevent.data

    # Aquí tienes que simular la estructura que daba el SDK de Firebase Functions
    # Usaremos el objeto 'after' para obtener los datos
    
    # 1. Obtener los DocumentSnapshots (usando la estructura de cloudevent.data)
    after_snapshot = event_data.get("value")
    before_snapshot = event_data.get("oldValue")

    # 2. Recrear tu lógica de solo creación
    # Una creación ocurre si oldValue es nulo (no existe) y value no es nulo (existe)
    is_creation = before_snapshot is None and after_snapshot is not None
    
    if not is_creation:
        logging.info("Event was not a document creation. Skipping function execution.")
        return

    # 3. Extraer el ID del documento
    # La ruta del recurso es: projects/.../documents/orders/orden_ID
    resource_name = after_snapshot.get("name")
    order_id = resource_name.split("/documents/orders/")[1]
    
    logging.info(f"SUCCESS: Triggered by new document in 'orders' collection. ID: {order_id}")
    
    try:
        # 4. Extraer los campos del documento
        # Los campos están en after_snapshot["fields"]
        new_order_data = {}
        for key, value in after_snapshot.get("fields", {}).items():
            # Esto es simplificado, en producción necesitarías un helper para parsear los tipos de Firestore
            new_order_data[key] = list(value.values())[0] if isinstance(value, dict) else value
        
        logging.info(f"Data for new order '{order_id}': {new_order_data}")

    except Exception as e:
        logging.error(f"Failed to extract data from new document '{order_id}': {e}")