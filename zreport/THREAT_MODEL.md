# Threat Model for IoT InfraLab (MVP)

This document defines the threat model and trust boundaries for the Minimum Viable Product (MVP) of the IoT InfraLab project.

## 1. Trust Boundaries

The system is divided into three primary zones with different levels of trust.

*   **Trusted Zone (Core Infrastructure):**
    *   **Components:** `mosquitto`, `nodered`
    *   **Trust Level:** High. These components are assumed to be configured correctly by the administrator, although the MQTT broker itself is intentionally vulnerable to demonstrate security flaws.
    *   **Boundary:** This zone is considered the internal, protected network.

*   **Hostile Zone (Attack Simulation):**
    *   **Components:** `docker_attacker`
    *   **Trust Level:** None. This component is explicitly untrusted and simulates an external or malicious actor.
    *   **Boundary:** It resides on the same Docker network but acts as an independent, hostile entity.

*   **Analytics & Monitoring Zone:**
    *   **Components:** `influxdb`, `grafana`, `loki`, `promtail`
    *   **Trust Level:** High. This zone is for data collection and visualization and is assumed to be secure and accessible only to administrators.

## 2. In-Scope Threats for MVP

The MVP focuses exclusively on demonstrating the detection of a **Denial-of-Service (DoS)** attack.

*   **Threat Actor:** A malicious script running in the `docker_attacker` container.
*   **Attack Vector:** The attacker connects to the vulnerable `mosquitto` broker and floods it with a high volume of connection requests or messages.
*   **Target:** The `mosquitto` MQTT broker.
*   **Intended Impact:** To overwhelm the broker, making it unavailable or unresponsive to legitimate clients (like the simulated sensor).
*   **Detection Mechanism:** `Suricata` inspects all traffic to and from the `mosquitto` service. A custom rule (`sid:1000001`) is configured to trigger an alert with the message `"DoS Attempt: MQTT SYN Flood Detected"` when it observes more than 100 SYN packets from a single source within 1 second.

## 3. Out-of-Scope Threats for MVP

The following threats are explicitly **out of scope** for the MVP demonstration:

*   Attacks on any service other than `mosquitto`.
*   Data injection, modification, or sniffing (e.g., `mqtt_inject`, `mqtt_sniff`).
*   Attacks originating from within the Trusted Zone (insider threats).
*   Exploits against the Docker runtime or the host machine.
*   Attacks on the analytics stack (Grafana, InfluxDB, etc.).
