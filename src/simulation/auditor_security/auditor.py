import os
import time
import nmap
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from google import genai

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# --- CONFIG ---
API_KEY = os.getenv("GEMINI_API_KEY")
BROKER = "mosquitto"
TARGET_SUBNET = "172.18.0.0/24" 
COOLDOWN_TIME = 30 

# --- PRE-FLIGHT VALIDATION ---
if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in environment variables.")
    # In a real app, you might want to exit here, but we'll let it 
    # try to connect to MQTT so you can at least see the status.

client_ai = genai.Client(api_key=API_KEY)
MODEL_ID = "gemini-2.0-flash"

last_scan_time = 0
is_scanning = False

# --- OPENTELEMETRY SETUP ---
_resource = Resource(attributes={
    "service.name": "security-auditor",
    "service.version": "1.0.0",
    "deployment.environment": "infralab"
})
_tracer_provider = TracerProvider(resource=_resource)
_otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
_tracer_provider.add_span_processor(BatchSpanProcessor(_otlp_exporter))
trace.set_tracer_provider(_tracer_provider)
tracer = trace.get_tracer(__name__)

def perform_audit():
    global last_scan_time, is_scanning, MODEL_ID
    is_scanning = True
    print(f"\n[INFO] Starting Security Audit at {time.strftime('%Y-%m-%d %H:%M:%S')}...")

    with tracer.start_as_current_span("audit_cycle") as audit_span:
        audit_span.set_attribute("target_subnet", TARGET_SUBNET)
        audit_span.set_attribute("model", MODEL_ID)

        try:
            # 1. INITIALIZATION CHECK
            if not API_KEY:
                raise ValueError("Missing API Key. Check your .env file.")

            print(f"[INFO] Using Gemini Model: {MODEL_ID}")
            client_mqtt.publish("lab/security/status", "Auditor Running...")

            # 2. SCANNING VALIDATION
            with tracer.start_as_current_span("nmap_scan") as scan_span:
                print(f"[INFO] Initiating Nmap scan on Subnet: {TARGET_SUBNET}")
                scan_span.set_attribute("target", TARGET_SUBNET)
                client_mqtt.publish("lab/security/status", "Scanning All Services...")
                nm = nmap.PortScanner()

                try:
                    nm.scan(hosts=TARGET_SUBNET, arguments='-sT -T4')
                except nmap.PortScannerError as e:
                    raise Exception(f"Nmap Error: Ensure container has NET_RAW capabilities. {e}")

                scan_summary = ""
                for host in nm.all_hosts():
                    for proto in nm[host].all_protocols():
                        ports = nm[host][proto].keys()
                        for port in ports:
                            if nm[host][proto][port]['state'] == 'open':
                                service = nm[host][proto][port]['name']
                                product = nm[host][proto][port]['product']
                                version = nm[host][proto][port]['version']
                                scan_summary += f"HOST: {host} | PORT: {port} | SERVICE: {service} | PRODUCT: {product} {version}\n"

                scan_span.set_attribute("hosts_scanned", len(nm.all_hosts()))
                print("[SUCCESS] Nmap scan completed.")
                print(f"--- Nmap Results ---\n{scan_summary if scan_summary else 'No open ports found.'}\n--------------------")

            # 3. EMPTY DATA GUARD
            if not scan_summary:
                print("[WARN] Audit Cancelled: No Hosts Found")
                client_mqtt.publish("lab/security/status", "Audit Cancelled: No Hosts Found")
                client_mqtt.publish("lab/security/report", "<h3>Scan Summary</h3><p>Network scan completed, but no active hosts with open ports were detected. Check your TARGET_SUBNET.</p>")
                return

            # 4. AI ANALYSIS & API VALIDATION
            with tracer.start_as_current_span("ai_analysis") as ai_span:
                print(f"[INFO] Sending structured scan data to Gemini AI ({MODEL_ID})...")
                ai_span.set_attribute("model", MODEL_ID)
                client_mqtt.publish("lab/security/status", "AI Analyzing Network & MQTT...")

                strict_prompt = f"""
                SYSTEM: You are a Zero-Trust Security Auditor.
                TASK: Analyze the CURRENT scan data provided below.

                CURRENT SCAN DATA:
                {scan_summary}

                CRITICAL RULES:
                1. DO NOT mention Port 111 or rpcbind.
                2. Focus on Port 1883 (MQTT) for SNIFFING risks.
                3. Analyze Port 1880 (Node-RED) and 8086 (InfluxDB).

                OUTPUT INSTRUCTIONS:
                You MUST return EXACTLY ONE <h3> header followed by ONE RAW HTML <table>.
                You MUST use exactly these 4 column headers in your <thead>: "Target Host", "Service", "Risk Analysis", "Security Recommendation".
                Use proper <thead>, <tbody>, <tr>, <th>, and <td> tags.
                DO NOT use markdown formatting (no ```html or pipes like |---|---|).
                DO NOT include any conversational text outside the HTML tags.
                """

                try:
                    response = client_ai.models.generate_content(
                        model=MODEL_ID,
                        contents=strict_prompt
                    )
                    ai_span.set_attribute("report_length", len(response.text))
                except Exception as ai_err:
                    err_str = str(ai_err)
                    ai_span.set_attribute("error", err_str)
                    if "429" in err_str:
                        raise Exception("API Quota Exhausted. Please wait or switch models.")
                    elif "503" in err_str:
                        raise Exception("AI Server Overloaded. Try again in 60 seconds.")
                    else:
                        raise Exception(f"AI Service Error: {err_str}")

            # 5. PUBLISH SUCCESS
            with tracer.start_as_current_span("publish_report") as pub_span:
                print("[SUCCESS] AI Analysis Complete. Publishing final report.")
                print(f"--- AI Report ---\n{response.text[:200]}...\n-----------------")
                client_mqtt.publish("lab/security/report", response.text)
                client_mqtt.publish("lab/security/status", "Audit Complete")
                pub_span.set_attribute("report_length", len(response.text))

        except Exception as e:
            audit_span.set_attribute("error", str(e))
            audit_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            error_msg = str(e)
            print(f"[ERROR] {error_msg}")
            client_mqtt.publish("lab/security/status", "Audit Error")
            client_mqtt.publish("lab/security/report", f"<h3 style='color:red'>System Error</h3><p>{error_msg}</p>")

        finally:
            is_scanning = False
            last_scan_time = time.time()
            print("[INFO] Audit thread finished, entering cooldown.\n")

# --- MQTT HANDLER ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[SUCCESS] Connected to MQTT Broker: {BROKER} on port 1883")
        client.subscribe([("lab/security/trigger", 0), ("lab/security/model", 0)])
        print(f"[INFO] Subscribed to topic: lab/security/trigger")
        print(f"[INFO] Subscribed to topic: lab/security/model")
        print(f"[INFO] Ready and waiting for commands...")
    else:
        print(f"❌ [CRITICAL] MQTT Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global last_scan_time, is_scanning, MODEL_ID
    payload = msg.payload.decode()
    
    if msg.topic == "lab/security/model":
        MODEL_ID = payload
        print(f"[CMD] Received model change request. New Model: {MODEL_ID}")
        client_mqtt.publish("lab/security/status", f"Model Set: {MODEL_ID}")
    
    elif msg.topic == "lab/security/trigger" and payload == "SCAN_NOW":
        print(f"[CMD] SCAN_NOW trigger received from dashboard.")
        # Check running state
        if is_scanning:
            print("[WARN] Scan attempted while system is already busy.")
            client_mqtt.publish("lab/security/status", "System Busy: Scan in Progress ⚠️")
            return
            
        # Check cooldown with countdown feedback
        time_passed = time.time() - last_scan_time
        if time_passed < COOLDOWN_TIME:
            wait_time = int(COOLDOWN_TIME - time_passed)
            print(f"[WARN] Scan attempted during cooldown. Retry in {wait_time}s.")
            client_mqtt.publish("lab/security/status", f"Cooldown: Wait {wait_time}s ⏳")
            return
            
        # VERY IMPORTANT FIX: Start audit in a separate thread so it doesn't block the MQTT Paho message loop!
        print("[INFO] Launching background audit thread execution...")
        threading.Thread(target=perform_audit, daemon=True).start()

# --- MQTT CONNECTION VALIDATION (set up in __main__ below, global for callbacks) ---
client_mqtt = None

if __name__ == "__main__":
    _client_mqtt = mqtt.Client(CallbackAPIVersion.VERSION1)
    _client_mqtt.on_connect = on_connect
    _client_mqtt.on_message = on_message

    try:
        print(f"\n[INFO] Starting Security Auditor...")
        print(f"[INFO] Connecting to Broker: {BROKER}...")
        _client_mqtt.connect(BROKER, 1883)
        _client_mqtt.loop_start()
        client_mqtt = _client_mqtt
    except Exception as e:
        print(f"❌ [CRITICAL] MQTT ERROR: Could not connect to {BROKER}. {e}")

    while True:
        time.sleep(1)