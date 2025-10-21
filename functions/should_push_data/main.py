import logging
import functions_framework
import json

# Importaciones movilizadas:
from google.events.cloud.firestore import DocumentEventData 
import firebase_admin

# Aseguramos el logging básico
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


@functions_framework.cloud_event
def should_push_data(cloudevent):
    """
    Recibe el evento binario de Firestore (CloudEvent Gen 2) y lo decodifica usando deserialize().
    """
    
    # --- Inicialización de Dependencias (Aislada) ---
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
            logging.info("Firebase Admin initialized successfully inside function.")
    except Exception as e:
        logging.error(f"RUNTIME ERROR: Firebase Admin failed to initialize: {e}")
        return "Internal Server Error: Init Failed", 500
    # ----------------------------------------------------------------------------------

    # El payload es binario (Protobuf)
    event_data_bytes = cloudevent.data
    
    try:
        # CORRECCIÓN CLAVE: Usar deserialize() para el payload binario
        firestore_event = DocumentEventData.deserialize(event_data_bytes) 
        
        # 1. Extraer Snapshots
        value = firestore_event.value 
        old_value = firestore_event.old_value

        # Lógica de verificación: Solo queremos la CREACIÓN
        if not old_value and value: 
            
            # 2. Extraer el ID del recurso
            resource_name = value.name
            try:
                # Obtenemos el ID del documento
                order_id = resource_name.split("/documents/orders/")[1]
            except IndexError:
                logging.error(f"Could not parse order_id from resource: {resource_name}")
                return "Invalid Resource Format", 400
            
            logging.info(f"SUCCESS: Triggered by new document. ID: {order_id}")

            # 3. Extraer Campos y decodificar los tipos de Firestore
            new_order_data = {}
            fields = value.fields if value and value.fields else {}
            
            for key, firestore_type_value in fields.items():
                # Decodificación simplificada de los tipos de campo de Firestore
                if isinstance(firestore_type_value, dict) and firestore_type_value:
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