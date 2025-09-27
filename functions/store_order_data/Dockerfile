# functions/store_order_data/Dockerfile

FROM python:3.12-slim

# Install necessary libraries for the function
RUN pip install functions-framework google-cloud-firestore

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY main.py .

# Expose the port where the function framework will listen
EXPOSE 8080

# This command starts the framework in a live-reloading debug mode
# It automatically reloads when it detects code changes in the mounted volume
ENTRYPOINT ["functions-framework", "--target", "store_order_data", "--port", "8080", "--debug"]