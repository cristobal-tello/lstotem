# functions/store_data/Dockerfile

FROM python:3.12-slim

# Set environment variables for production/non-interactive use
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file AND install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

EXPOSE 8080

ENTRYPOINT ["functions-framework", \
             "--target", "store_data", \
             "--port", "8080"]