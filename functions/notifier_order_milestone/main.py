# main.py para notifier_order_milestone

import logging
import firebase_admin
import functions_framework
import json

# LIBRERÍA CLAVE: Usamos google.events para decodificar el payload binario de Firestore (Protobuf)
# Asegúrate que google-events está en requirements.txt
from google.events.cloud.firestore import v1 as firestoredata

# Inicializa Firebase Admin SDK (útil si accedes a otros servicios de Firebase)
firebase_admin.initialize_app()
logging.basicConfig(level=logging.INFO)

# CAMBIO CLAVE: Usamos el decorador estándar de CloudEvent de functions-framework
# para asegurar la firma de UN solo argumento.
@functions_framework.cloud_event
def notifier_order_milestone(cloudevent):
    """
    Recibe el evento binario de Firestore y lo decodifica usando Protobuf.
    """
    
    # 1. Obtener los bytes de datos binarios
    event_data_bytes = cloudevent.data
    
    try:
        # 2. Decodificar los bytes binarios de Protobuf
        # Usamos from_json() con el payload, ya que cloudevent.data viene como una estructura que from_json puede interpretar.
        # Si esto da error, intenta DocumentEventData.deserialize(event_data_bytes)
        firestore_event = firestoredata.DocumentEventData.from_json(event_data_bytes)
        
        # 3. Extraer Snapshots
        value = firestore_event.value 
        old_value = firestore_event.old_value

        # Lógica de verificación de creación
        if not old_value and value: 
            
            # 4. Extraer el ID del recurso
            resource_name = value.name
            # La ruta es projects/.../databases/(default)/documents/orders/ID_DOCUMENTO
            order_id = resource_name.split("/documents/orders/")[1]
            logging.info(f"SUCCESS: Triggered by new document. ID: {order_id}")

            # 5. Obtener los campos del documento (esto requiere otro paso de parsing o librería)
            # Para simplificar, solo loguearemos el ID, ya que decodificar fields es complejo
            logging.info(f"Document fields received.")
            
        else:
            logging.info("Event was not a document creation (update/delete). Skipping.")

    except Exception as e:
        logging.error(f"FATAL ERROR: Failed to parse CloudEvent/Protobuf data: {e}")
        # Es crucial retornar aquí para evitar reintentos si el error no es temporal
        return "Parsing Error", 400