# main.py para notifier_order_milestone (Máxima Estabilidad)

# Solo importamos lo ABSOLUTAMENTE necesario para que el FRAMEWORK arranque
import functions_framework
import logging

# No importar firebase_admin, google.events, etc. aquí.
# Las moveremos dentro de la función.

# Aseguramos el logging básico
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

# La función principal, con un solo argumento para asegurar la compatibilidad Gen 2
@functions_framework.cloud_event
def notifier_order_milestone(cloudevent):
    # --- INICIALIZACIÓN MOVILIZADA (Para evitar fallos en el arranque) ---
    import firebase_admin
    from google.events.cloud.firestore import v1 as firestoredata
    
    # Inicialización de Firebase Admin solo si no está inicializada
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
            logging.info("Firebase Admin initialized successfully inside function.")
    except Exception as e:
        logging.error(f"RUNTIME ERROR: Firebase Admin failed to initialize: {e}")
        return "Internal Server Error", 500
    # ------------------------------------------------------------------------

    event_data_bytes = cloudevent.data
    
    try:
        # Usa DocumentEventData para decodificar los bytes Protobuf.
        firestore_event = firestoredata.DocumentEventData.from_json(event_data_bytes)
        
        # ... (Aquí va el resto de tu lógica de parsing de firestore_event) ...
        value = firestore_event.value 
        old_value = firestore_event.old_value
        
        if not old_value and value: 
            resource_name = value.name
            # La ruta es projects/.../databases/(default)/documents/orders/ID_DOCUMENTO
            order_id = resource_name.split("/documents/orders/")[1]
            logging.info(f"SUCCESS: Triggered by new document. ID: {order_id}")
        else:
            logging.info("Event was not a document creation. Skipping.")

        return "OK"

    except Exception as e:
        logging.error(f"RUNTIME ERROR: Failed to process event data: {e}")
        return "Internal Server Error", 500