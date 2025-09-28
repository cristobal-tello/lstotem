I need to create a decoupled application using Google Cloud.
The goal is for a Prestashop web shop, running in a Google Cloud VM, to write a message to a specific topic.
For now, the data stored in the message sent to the topic is: order ID, order date, order total, payment type, and delivery type.
The part to send data to a particular topic from Prestashop it is clear. We need to focus on next issues.

1. Save data from the subscription
   A subscription listening to that topic needs to store this data somewhere. (Please provide recommendations based on the following details).
   The data needs to be stored in the same Google Cloud project but not in the same VM; it must be a separate service.
2. Build simple web app
   When a certain number of orders (e.g., 10, 20, 30) is reached on the same day, an event needs to be sent to this web app
   When event is raise, the webapp display a congrats message showiing the total of the orders reached.
   This web app also cannot be on the VM and must be another separate service but it the same Google Cloud project.

---

Here's a high-level overview of the components we'll use:

1. Prestashop (on Google Compute Engine VM): Publishes messages to a Pub/Sub topic.
2. Cloud Pub/Sub: Decouples the Prestashop application from the data processing and web application.
3. Cloud Function (or Cloud Run): Subscribes to the Pub/Sub topic, processes the messages, and stores them.
4. Firestore (or Cloud SQL/BigQuery): Stores the order data.
5. Cloud Function (or Cloud Run): A second function/service triggered by an event (e.g., reaching a certain order count) that interacts with your web app.
6. Cloud Run (or App Engine Standard): Hosts your simple web application.

I've decided next names:

Topic name: prestashop-order-data
Subscription: prestashop-order-data-sub

I'll use Google Cloud shell in order to send data to the topic.

gcloud pubsub topics publish prestashop-order-data --message='{"orderId": "'"$RANDOM"'", "dateOrder": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "totalOrder": "'"$((RANDOM%500 + 100))"'.00", "paymentType": "credit_card", "deliveryType": "standard"}'

Also, to pull a message from the subscription to test it (auto-acknowledges the message)
gcloud pubsub subscriptions pull prestashop-order-data-sub --auto-ack --limit=1

I have a subscription that get the message from a topic, the message is:
{"orderId": "20124", "dateOrder": "2025-09-25T21:16:32Z", "totalOrder": "178.00", "paymentType": "credit_card", "deliveryType": "standard"}

I need a way to store this data from the subscription, save it and ack the subscription. How I can do that?
Remember, later these data will be consumed in order to get total of a particular day

I’m using Google Cloud Run, I just created a subscription and now I need to create a google cloud function in order to get the data from the subscription and store this data to be consumed later.

I need to start with the local setup in order to create a google function in my local dev. I don't want to install the dependencies in the local computer, instead I want to use docker. This the goal

Give a the step to create a local development environment using docker and visual studio
The cloud function will be written using Python.
I want to “simulate” the same way as we Google Cloud Function will run in Google Cloud, so how to setup a local database in local env
Debug the cloud function from Visual studio code
When the function is ready, I’ll do a push into a git repository. Then some kind of event needs to be fired to deploy the function to production.

So, this is my main.py in the store_order_data directory: import base64
import json
import functions_framework
from google.cloud import firestore

# Initialize the Firestore client

db = firestore.Client()

@functions_framework.cloud_event
def store_order_data(cloud_event):
"""
Cloud Function triggered by a message on a Pub/Sub topic.
It parses the order data and saves it to Firestore.

    Args:
        cloud_event (cloudevents.http.CloudEvent): The event payload.
    """
    # The actual data is in the 'message' field, base64-encoded.
    try:
        message_data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        order_data = json.loads(message_data)
        print(f"Received order data: {order_data}")
    except (KeyError, json.JSONDecodeError, TypeError) as e:
        print(f"Error decoding message: {e}")
        # Return a non-2xx status to indicate failure, causing a NACK
        return "Bad Request: Invalid message format", 400

    # --- Data Validation and Transformation ---
    # It's a best practice to validate and convert data types.
    try:
        order_id = str(order_data["orderId"])
        # Convert totalOrder to a float for calculations
        order_data["totalOrder"] = float(order_data["totalOrder"])
        # Convert dateOrder string to a Firestore timestamp for proper querying
        order_data["dateOrder"] = firestore.SERVER_TIMESTAMP
    except (KeyError, ValueError) as e:
        print(f"Error processing order data: {e}")
        return "Bad Request: Missing or invalid data fields", 400

    # --- Store in Firestore ---
    # Use the orderId as the document ID for easy lookups and to prevent duplicates.
    doc_ref = db.collection("orders").document(order_id)
    doc_ref.set(order_data)

    print(f"Successfully stored order {order_id} in Firestore.")
    # A successful return (or None) will automatically ACK the message.

# Define the order data as a JSON string

PAYLOAD='{"orderId": "MAKE-TEST-'"$(date +%s)"'", "dateOrder": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'", "totalOrder": "125.75", "paymentType": "credit_card", "deliveryType": "standard"}'

# Base64 encode the JSON string

BASE64_PAYLOAD=$(printf '%s' "$PAYLOAD" | base64 | tr -d '\n')

# Use curl to send the CloudEvent with the correctly encoded payload

curl -sS -X POST http://localhost:8080 \
 -H "Content-Type: application/json" \
 -H "ce-id: $(uuidgen)" \
     -H "ce-specversion: 1.0" \
     -H "ce-time: $(date -u +"%Y-%m-%dT%H:%M:%S.000Z")" \
     -H "ce-type: google.cloud.pubsub.topic.v1.messagePublished" \
     -H "ce-source: //pubsub.googleapis.com/projects/your-project-id/topics/prestashop-order-data" \
     -d "$(printf '{"message":{"data":"%s"}}' "$BASE64_PAYLOAD")"

# Use curl to check if data is properly persisted

curl -s -X POST "http://localhost:8082/v1/projects/lstotem/databases/(default)/documents:runQuery" -H "Content-Type: application/json" -d '{"structuredQuery":{"from":[{"collectionId":"orders"}]}}'

Perfect. You have completed the local development and testing phase. Now that your code is in a Git repository, the next step is to set up a continuous deployment pipeline to get your function into production.

The best way to do this on Google Cloud is by using Cloud Build to automate the deployment process. This approach ensures that every time you push a change to your Git repository, your function is automatically and consistently deployed.

Create the cloudbuild.yaml File
This file is the most important part of the deployment. It tells Cloud Build exactly what steps to take to build and deploy your function. It should be placed in the root of your project, alongside your functions/ directory.

Don't forget to enable Cloud Function API
You need to enable the Cloud Functions API because deploying a Cloud Function is an API operation performed by the Google Cloud SDK (gcloud), which runs within your Cloud Build job.

Also Cloud Resource Manager API, Eventarc API, Cloud Run API
