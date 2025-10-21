FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file AND install dependencies
# This is where the upgrade must happen!
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY main.py .

# Correct ENTRYPOINT (remove the --log-level flag, as discussed)
ENTRYPOINT ["functions-framework", \
            "--target", "should_push_data", \
            "--port", "8080", \
            "--debug"]