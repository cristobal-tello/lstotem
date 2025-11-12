include .env

APP_NAME=$(GOOGLE_CLOUD_PROJECT)_app
PUSHER_MSG=$(MESSAGE)$(shell od -An -N2 -i /dev/random | tr -d ' ')

up:
	@echo "Building and starting services..."
	docker compose up --build -d

build:
	@echo "Building the 'store-data' service image..."
	docker compose build store-data

down:
	@echo "Stopping and removing all services..."
	docker compose down

logs:
	@echo "Showing logs for all services..."
	docker compose logs -f

clean:
	@echo "Stopping and removing all services and the firestore-data volume..."
	docker compose down -v

create_topic:
	@echo "Creating Pub/Sub topic: prestashop-order-data..."
	@curl -sS -X PUT http://localhost:8085/v1/projects/lstotem/topics/prestashop-order-data

create_subscription:
	echo "Creating Subscription: prestashop-order-data-sub, linking to store-data function..."
	@curl -sS -X PUT http://localhost:8085/v1/projects/lstotem/subscriptions/prestashop-order-data-sub \
  		-H "Content-Type: application/json" \
  		-d '{"topic": "projects/lstotem/topics/prestashop-order-data", "pushConfig": {"pushEndpoint": "http://lstotem_store-data:8080"}}'

publish_to_topic:
# Why your-project-id in "//pubsub.googleapis.com/projects/your-project-id/topics/prestashop-order-data"" is Ignored Locally
# The emulator relies on the environment variable GOOGLE_CLOUD_PROJECT for its project context.
	@echo "Sending test Pub/Sub message..."
	@epoch=$$(date +%s); \
	now=$$(date -u +"%Y-%m-%dT%H:%M:%SZ"); \
	payload=$$(printf '{"orderId":"MAKE-TEST-%s","dateOrder":"%s","totalOrder":"125.75","paymentType":"credit_card","deliveryType":"standard"}' "$$epoch" "$$now"); \
	b64=$$(printf '%s' "$$payload" | base64 | tr -d '\n'); \
	curl -sS -X POST http://localhost:8085/v1/projects/lstotem/topics/prestashop-order-data:publish \
  	-H "Content-Type: application/json" \
  	-d "$$(printf '{"messages": [{"data": "%s"}]}' "$$b64")"

store_data_log:
	docker logs lstotem_store-data

should_push_data_log:
	docker logs lstotem_should-push-data

firestore_log:
	docker logs lstotem_firestore-emulator

firestore_list_orders:
	@echo "Querying $(COLLECTION) on $(PROJECT_NAME)..."
	@curl -s -X POST "http://localhost:8082/v1/projects/lstotem/databases/(default)/documents:runQuery" \
	  -H "Content-Type: application/json" \
	  -d '{"structuredQuery":{"from":[{"collectionId":"orders"}]}}'

milestone_log:
	docker compose logs -f notifier-order-milestone

web_bash:
	docker exec -it lstotem_web bash # Open an interactive bash shell in the running container

web_log:
	docker logs lstotem_web

web_push:
	@echo "--- Triggering Pusher Event on [$(PUSHER_CHANNEL)] with Data: $(PUSHER_MSG) ---"
	@JSON_PAYLOAD=$$(printf '{"name":"%s","channel":"%s","data":"%s"}' "$(PUSHER_EVENT)" "$(PUSHER_CHANNEL)" "$(PUSHER_MSG)"); \
	BODY_MD5=$$(printf "%s" "$$JSON_PAYLOAD" | openssl md5 -binary | xxd -p -c 256); \
	TIMESTAMP=$$(date +%s); \
	STRING_TO_SIGN=$$(printf "POST\n/apps/%s/events\nauth_key=%s&auth_timestamp=%s&auth_version=1.0&body_md5=%s" "$(PUSHER_APP_ID)" "$(PUSHER_APP_KEY)" $$TIMESTAMP $$BODY_MD5); \
	SIGNATURE=$$(printf "%s" "$$STRING_TO_SIGN" | openssl dgst -sha256 -hmac "$(PUSHER_APP_SECRET)" | cut -d ' ' -f2); \
	curl -s -X POST "https://api-$(PUSHER_CLUSTER).pusher.com/apps/$(PUSHER_APP_ID)/events?auth_key=$(PUSHER_APP_KEY)&auth_timestamp=$$TIMESTAMP&auth_version=1.0&body_md5=$$BODY_MD5&auth_signature=$$SIGNATURE" \
		-H "Content-Type: application/json" \
		-d "$$JSON_PAYLOAD" \
	&& echo "✅ Event sent successfully!" || echo "❌ Failed to send event"
