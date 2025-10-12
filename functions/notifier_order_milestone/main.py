# main.py para notifier_order_milestone

import logging
import functions_framework
import json

# Importaciones movilizadas:
# El framework de funciones se encarga de cargar estas, pero las llamamos aquí.
# Corrección CLAVE: Importamos DocumentEventData directamente, sin usar 'v1'.
from google.events.cloud.firestore import DocumentEventData 
import firebase_admin

# Aseguramos el logging básico
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


@functions_framework.cloud_event
def notifier_order_milestone(cloudevent):
    """
    Recibe el evento binario de Firestore (CloudEvent Gen 2) y lo decodifica.
    """
    
    # --- Inicialización de Dependencias (Aislada para evitar Healthcheck failed) ---
    try:
        # Inicializa Firebase Admin solo si no está inicializada.
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
            logging.info("Firebase Admin initialized successfully inside function.")
    except Exception as e:
        logging.error(f"RUNTIME ERROR: Firebase Admin failed to initialize: {e}")
        # Retornamos 500 para evitar que Firestore reintente inmediatamente.
        return "Internal Server Error: Init Failed", 500
    # ----------------------------------------------------------------------------------

    # El payload es binario (Protobuf), lo pasamos al parser
    event_data_bytes = cloudevent.data
    
    try:
        # 1. Decodificar los bytes binarios de Protobuf usando la clase correcta
        # DocumentEventData.from_json() decodifica la estructura del payload binario.
        firestore_event = DocumentEventData.from_json(event_data_bytes) 
        
        # 2. Extraer Snapshots
        value = firestore_event.value 
        old_value = firestore_event.old_value

        # Lógica de verificación: Solo queremos la CREACIÓN
        if not old_value and value: 
            
            # 3. Extraer el ID del recurso y los datos
            resource_name = value.name
            
            # La ruta completa del documento (ejemplo: .../documents/orders/ID_DOCUMENTO)
            try:
                # Obtenemos el ID del documento
                order_id = resource_name.split("/documents/orders/")[1]
            except IndexError:
                logging.error(f"Could not parse order_id from resource: {resource_name}")
                return "Invalid Resource Format", 400
            
            logging.info(f"SUCCESS: Triggered by new document. ID: {order_id}")

            # 4. Extraer Campos (Requiere parsear los tipos de Firestore: stringValue, etc.)
            new_order_data = {}
            fields = value.fields if value and value.fields else {}
            
            for key, firestore_type_value in fields.items():
                # Esta es una decodificación simplificada de los tipos de campo de Firestore (integerValue, stringValue, etc.)
                if isinstance(firestore_type_value, dict):
                    # El valor es el primer (y único) valor en el diccionario (ej: {"stringValue": "valor"})
                    new_order_data[key] = list(firestore_type_value.values())[0]
                else:
                    new_order_data[key] = firestore_type_value

            logging.info(f"Data for new order '{order_id}': {new_order_data}")

        else:
            logging.info("Event was not a document creation. Skipping.")

        return "OK"

    except Exception as e:
        # Captura cualquier error de parsing o lógica
        logging.error(f"FATAL RUNTIME ERROR: Failed to process event data: {e}", exc_info=True)
        return "Internal Server Error", 500