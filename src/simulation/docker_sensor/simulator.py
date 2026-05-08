import paho.mqtt.client as mqtt
import time
import random
import os
import json

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Environment variables from Docker (Passed by Node-RED)
SENSOR_ID = os.getenv("SENSOR_ID", "sensor_node")
SENSOR_TYPES = [s.strip() for s in os.getenv("SENSOR_TYPES", "temperature").split(',')]
NODE_PROFILE = os.getenv("NODE_PROFILE", "normal").lower()
INTERVAL = int(os.getenv("INTERVAL", "5"))
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

# Global variables for dynamic config
DYNAMIC_BLUEPRINTS = {}
BASE_RANGES = {}
CONFIG_FILE = "/app/config/sensor_settings.json"
SENSOR_TYPES_FILE = "/app/config/sensor_types.json"

def load_config():
    global SENSOR_TYPES, DYNAMIC_BLUEPRINTS, BASE_RANGES
    
    if os.path.exists(SENSOR_TYPES_FILE):
        try:
            with open(SENSOR_TYPES_FILE, 'r') as f:
                BASE_RANGES = json.load(f)
        except Exception as e:
            print(f"[{SENSOR_ID}] Error loading sensor types: {e}")

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                # Extract blueprints if defined
                if "blueprints" in config:
                    DYNAMIC_BLUEPRINTS = config["blueprints"]
                
                # Check if this sensor has a specific override
                sensors = config.get("sensors", {})
                if SENSOR_ID in sensors:
                    sensor_conf = sensors[SENSOR_ID]
                    if "types" in sensor_conf:
                        SENSOR_TYPES = [s.strip() for s in sensor_conf["types"]]
            print(f"[{SENSOR_ID}] Config reloaded. New types: {SENSOR_TYPES}")
        except Exception as e:
            print(f"[{SENSOR_ID}] Error loading config: {e}")

# OpenTelemetry configuration
resource = Resource(attributes={"service.name": os.getenv("OTEL_SERVICE_NAME", f"iot-sensor-node-{SENSOR_ID}")})
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

# For the "failing" profile
start_time = time.time()

def get_sensor_value(s_type, profile, elapsed):
    # Use loaded base ranges
    ranges = dict(BASE_RANGES)
    
    # Overwrite range if defined dynamically
    if s_type in DYNAMIC_BLUEPRINTS and "range" in DYNAMIC_BLUEPRINTS[s_type]:
        ranges[s_type] = tuple(DYNAMIC_BLUEPRINTS[s_type]["range"])

    base_min, base_max = ranges.get(s_type, (0.0, 100.0))
    val = random.uniform(base_min, base_max)

    # Apply behavioral profile rules
    if profile == "failing":
        # Simulate gradual deterioration: drift upward by 5% every 30 seconds
        drift_factor = 1.0 + (elapsed / 30.0) * 0.05
        val *= drift_factor
    elif profile == "erratic":
        # 10% chance to generate an extreme spike (2x to 4x baseline)
        if random.random() < 0.1:
            val *= random.uniform(2.0, 4.0)

    # Format output
    if s_type == "vibration":
        return round(val, 3) # Vibration needs higher precision
    return round(val, 1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[{SENSOR_ID}] Connected to MQTT broker: {MQTT_BROKER}")
        client.subscribe("cmd/system/reload")
    else:
        print(f"[{SENSOR_ID}] Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    if msg.topic == "cmd/system/reload":
        print(f"[{SENSOR_ID}] Received reload command!")
        load_config()

def main():
    client = mqtt.Client(SENSOR_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Load initial config if present
    load_config()

    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.loop_start()
    except Exception as e:
        print(f"[{SENSOR_ID}] Could not connect to broker: {e}")
        return

    print(f"[{SENSOR_ID}] Starting dynamic simulation (Profile: {NODE_PROFILE})...")
    topic = f"sensors/factory/{SENSOR_ID}"
    
    try:
        while True:
            elapsed = time.time() - start_time
            readings = {}
            for s_type in SENSOR_TYPES:
                readings[s_type] = get_sensor_value(s_type, NODE_PROFILE, elapsed)

            payload = json.dumps({
                "sensor_id": SENSOR_ID,
                "profile": NODE_PROFILE,
                "readings": readings,
                "timestamp": time.time()
            })
            
            with tracer.start_as_current_span(f"mqtt_publish_{topic}"):
                client.publish(topic, payload)
                print(f"[{SENSOR_ID}] Published: {payload}")
                
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print(f"\n[{SENSOR_ID}] Shutting down...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
