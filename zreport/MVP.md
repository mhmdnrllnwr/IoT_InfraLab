# Minimum Viable Product (MVP)

This document defines the Minimum Viable Product (MVP) for the IoT InfraLab project, as required to address feasibility and prioritization feedback. The MVP represents the core functionality that **must** be delivered and working by the end of the semester.

## MVP Core Objective

To create a functional, end-to-end simulation of a single, specific IoT security threat, from attack generation to detection and visualization, within a containerized environment.

## Key Components & Features for MVP

The following components must be functional and integrated:

1.  **Core Infrastructure (Trusted Zone):**
    *   `mosquitto`: The MQTT broker, using the `mosquitto_vulnerable.conf` configuration.
    *   `nodered`: Capable of managing the lifecycle (create, start, stop) of a single simulated sensor.

2.  **Sensor Simulation:**
    *   `docker_sensor`: A single simulated sensor container that connects to Mosquitto and publishes telemetry to a specific topic (e.g., `sensors/temp/room1`).

3.  **Attack Simulation:**
    *   `docker_attacker`: A single attacker container capable of launching one specific, documented attack.
    *   **MVP Attack:** MQTT Denial-of-Service (DoS) attack against the broker (`mqtt_dos.py`).

4.  **Intrusion Detection:**
    *   `suricata`: Running and inspecting the Mosquitto network traffic.
    *   Must have at least one custom rule in `local.rules` capable of detecting the MVP's MQTT DoS attack.
    *   Must generate a corresponding alert in `infrastructure/suricata/logs/eve.json`.

5.  **Observability & Visualization:**
    *   `influxdb`: To receive the sensor's telemetry.
    *   `grafana`: To display a simple dashboard with two panels:
        *   One panel showing the live telemetry from the single sensor.
        *   One panel showing the Suricata alert count (or a log panel showing the specific alert).
    *   `loki` & `promtail`: To receive and display Suricata logs in Grafana.

## Out of Scope for MVP (Nice-to-Have)

The following features are considered extensions and are not required for the MVP:
*   Multiple, concurrent sensor simulations.
*   Advanced attack scenarios (e.g., MQTT inject, sniff).
*   The `security-auditor` service (the `docker_attacker` is sufficient for the MVP).
*   Dynamic IDS/IPS rule toggling from Node-RED.
*   Advanced Grafana dashboards, tracing with Tempo, or complex OTEL configurations.
*   Performance stress testing and defining maximum node limits.
*   SDG 4 mapping and educational features.

## MVP Evaluation Criteria

The MVP will be considered successful if the following end-to-end scenario can be demonstrated:

1.  The full stack is deployed with `docker compose up -d`.
2.  The Node-RED UI can be used to start one sensor container.
3.  The Grafana dashboard correctly displays the sensor's telemetry.
4.  The `docker_attacker` is manually executed to launch the MQTT DoS attack.
5.  The Suricata alert for the DoS attack appears in the Grafana dashboard within **10 seconds** of the attack starting.
6.  The system remains stable during the test.
