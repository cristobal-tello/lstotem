# notifier_order_milestone.py

import logging
import firebase_admin
import json # <-- ¡Necesitas esta importación!

# Importar las librerías necesarias
from google.cloud import firestore
import functions_framework 

# ... (resto de las inicializaciones)

@functions_framework.cloud_event
def notifier_order_milestone(cloudevent):
    """
    Triggers on new order creation and logs the data of the inserted document.
    """
    
    # CORRECCIÓN CLAVE: Decodificar el payload
    if isinstance(cloudevent.data, bytes):
        event_data_bytes = cloudevent.data
        # Intenta decodificar de JSON
        try:
            event_data = json.loads(event_data_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logging.error("Failed to decode CloudEvent data into JSON.")
            return
    elif isinstance(cloudevent.data, dict):
        # Si ya es un diccionario (menos común, pero manejable)
        event_data = cloudevent.data
    else:
        logging.error(f"Unexpected data type received: {type(cloudevent.data)}")
        return

    # Aquí comienza tu lógica original, ahora con 'event_data' como diccionario
    
    # 1. Obtener los DocumentSnapshots
    after_snapshot = event_data.get("value")
    before_snapshot = event_data.get("oldValue")

    # 2. Recrear tu lógica de solo creación
    is_creation = before_snapshot is None and after_snapshot is not None
    
    if not is_creation:
        logging.info("Event was not a document creation. Skipping function execution.")
        return

    # 3. Extraer el ID del documento
    # La ruta del recurso está en el snapshot 'value'
    resource_name = after_snapshot.get("name")
    # Manejo de error si el resource_name no tiene el formato esperado
    try:
        order_id = resource_name.split("/documents/orders/")[1]
    except (AttributeError, IndexError):
        logging.error(f"Could not parse order_id from resource name: {resource_name}")
        return
    
    logging.info(f"SUCCESS: Triggered by new document in 'orders' collection. ID: {order_id}")
    
    try:
        # 4. Extraer los campos del documento (esta lógica es correcta si el JSON es plano)
        new_order_data = {}
        for key, value in after_snapshot.get("fields", {}).items():
            # Esta línea asume que cada valor es un tipo de Firestore anidado (stringValue, integerValue, etc.)
            new_order_data[key] = list(value.values())[0] if isinstance(value, dict) and value else value
        
        logging.info(f"Data for new order '{order_id}': {new_order_data}")

    except Exception as e:
        logging.error(f"Failed to extract data from new document '{order_id}': {e}")