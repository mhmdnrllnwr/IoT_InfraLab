FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator script
COPY simulator.py .

# Environment variables with defaults
ENV SENSOR_ID=sensor_1
ENV SENSOR_TYPE=temperature
ENV INTERVAL=5
ENV MQTT_BROKER=mosquitto

# Command to run the simulator
CMD ["python", "-u", "simulator.py"]
