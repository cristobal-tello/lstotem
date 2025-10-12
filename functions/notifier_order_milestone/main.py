# main.py para notifier_order_milestone (Con Initialisation Check)

import logging
import firebase_admin
import functions_framework
import json
from google.events.cloud.firestore import v1 as firestoredata

# --- INICIALIZACIÓN GLOBALES ---
# Ejecutar initialize_app() dentro de un bloque try para que el framework se inicie
try:
    firebase_admin.initialize_app()
    logging.info("Firebase Admin initialized successfully.")
except Exception as e:
    # Esto no debería pasar, pero si lo hace, no debe detener el arranque del container.
    logging.error(f"FATAL INIT ERROR: Firebase Admin failed to initialize: {e}")
    # Nota: Si falla aquí, las llamadas a Firebase dentro de la función fallarán.

logging.basicConfig(level=logging.INFO)

# --- FUNCIÓN PRINCIPAL ---
@functions_framework.cloud_event
def notifier_order_milestone(cloudevent):
    """
    Recibe el evento binario de Firestore y lo decodifica usando Protobuf.
    """
    
    event_data_bytes = cloudevent.data
    
    try:
        # Usa DocumentEventData para decodificar los bytes Protobuf.
        # Esto asume que el payload de cloudevent.data es la data binaria del evento Firestore.
        # Si esto falla, puede ser porque el payload no es puro Protobuf.
        firestore_event = firestoredata.DocumentEventData.from_json(event_data_bytes) 
        
        # ... (resto de la lógica de parsing de firestore_event) ...
        # (tu código de parsing anterior va aquí)
        
        value = firestore_event.value 
        old_value = firestore_event.old_value
        
        if not old_value and value:
            resource_name = value.name
            order_id = resource_name.split("/documents/orders/")[1]
            logging.info(f"SUCCESS: Triggered by new document. ID: {order_id}")
        else:
            logging.info("Event was not a document creation. Skipping.")

    except Exception as e:
        # Si algo falla en la lógica de la función, al menos el contenedor ya está UP.
        logging.error(f"RUNTIME ERROR: Failed to process event data: {e}")
        return "Internal Server Error", 500