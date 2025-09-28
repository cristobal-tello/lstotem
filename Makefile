PROJECT_NAME=ls_totem
APP_NAME=$(PROJECT_NAME)_app

up:
	@echo "Building and starting services..."
	docker-compose up --build -d

build:
	@echo "Building the 'store-order-data' service image..."
	docker-compose build store-order-data

down:
	@echo "Stopping and removing all services..."
	docker-compose down

logs:
	@echo "Showing logs for all services..."
	docker-compose logs -f

clean:
	@echo "Stopping and removing all services and the firestore-data volume..."
	docker-compose down -v

send_message:
	@echo "Sending test Pub/Sub message..."
	@epoch=$$(date +%s); \
	now=$$(date -u +"%Y-%m-%dT%H:%M:%SZ"); \
	payload=$$(printf '{"orderId":"MAKE-TEST-%s","dateOrder":"%s","totalOrder":"125.75","paymentType":"credit_card","deliveryType":"standard"}' "$$epoch" "$$now"); \
	b64=$$(printf '%s' "$$payload" | base64 | tr -d '\n'); \
	curl -sS -X POST http://localhost:8080 \
	  -H "Content-Type: application/json" \
	  -H "ce-id: $$(uuidgen)" \
	  -H "ce-specversion: 1.0" \
	  -H "ce-time: $$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")" \
	  -H "ce-type: google.cloud.pubsub.topic.v1.messagePublished" \
	  -H "ce-source: //pubsub.googleapis.com/projects/your-project-id/topics/prestashop-order-data" \
	  -d "$$(printf '{"message":{"data":"%s"}}' "$$b64")"

list_orders:
	@echo "Querying $(COLLECTION) on $(PROJECT_NAME)..."
	@curl -s -X POST "http://localhost:8082/v1/projects/lstotem/databases/(default)/documents:runQuery" \
	  -H "Content-Type: application/json" \
	  -d '{"structuredQuery":{"from":[{"collectionId":"orders"}]}}'
