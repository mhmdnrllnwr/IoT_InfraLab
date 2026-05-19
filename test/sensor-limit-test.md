# Sensor Container Limit Test Report

**Date:** 2026-05-19  
**Environment:** Docker Desktop (WSL2), 4GB VM, 12 vCPUs  
**Image:** `general-iot-sensor:latest` (238MB, python:3.9-slim)  
**Network:** `iot_infralab_net` (172.18.0.0/24)

---

## Method

Created sensor containers in batches of 10 with `--memory=64m --memory-reservation=32m`. Each sensor publishes DHT11 reading to MQTT every 5s. Monitored RAM, CPU, Docker daemon health, and MQTT between batches.

## Results

| Batch | Sensors | Total Sensor RAM | Avg/Sensor | Infra Status | Notes |
|-------|---------|-----------------|------------|--------------|-------|
| 1 | 10 | ~260 MiB | ~26 MiB | Healthy | MQTT publishing OK |
| 2 | 20 | ~520 MiB | ~26 MiB | Healthy | |
| 3 | 30 | ~754 MiB | ~25 MiB | Healthy | |
| 4 | 40 | ~956 MiB | ~24 MiB | Healthy | |
| 5 | 50 | ~956 MiB | ~19 MiB | InfluxDB 67% CPU | Write pressure rising |
| 6 | 60 | ~947 MiB | ~16 MiB | InfluxDB 87% CPU | Mosquitto still 2.4MiB |
| 7 | ~64 | - | - | **Docker daemon 500 error** | WSL2 VM OOM |

## Constraints Identified

### 1. Docker Daemon RAM (Hard Limit)
Docker Desktop WSL2 VM has ~3.8GiB allocatable. At ~64 containers, WSL2 VM exhausted memory, Docker daemon returned HTTP 500. This is the primary hard cap.

### 2. InfluxDB Write Pressure (Soft Limit)
At 50+ sensors (10 publishes/sec), InfluxDB CPU reached 67-87%. InfluxDB is memory-limited to 512MiB; beyond ~60 sensors, write latency degrades.

### 3. Mosquitto MQTT Broker
Negligible impact. Used 2.4MiB RAM at 60 sensors. MQTT is not the bottleneck.

### 4. Network (Subnet)
/24 subnet = 254 IPs. Only ~12 used by infra + ~64 test = 76 total. Not a constraint.

## Limits Summary

| Limit | Value | Bottleneck |
|-------|-------|------------|
| **Safe operational** | **40-50 sensors** | InfluxDB write headroom |
| **Stressed** | 50-60 sensors | InfluxDB CPU >80% |
| **Hard crash** | ~64 sensors | Docker WSL2 VM OOM |

## Recommendations

- **Set `--memory=32m`** instead of 64m per sensor to increase density (~2x more per GB)
- **Increase InfluxDB memory limit** from 512MiB to 1GiB if host RAM available
- **Increase Docker Desktop WSL2 RAM** in Settings → Resources → Advanced if host has >8GB
- **Batch creates** when scaling up — creating 10 at once takes ~5s, creating 60+ at once risks daemon timeout

## Docker Compose Resource Audit

| Service | Limit | Usage at 60 sensors | Headroom |
|---------|-------|-------------------|----------|
| Mosquitto | 64m | 2.4m | 96% |
| Node-RED | 384m | 90m | 77% |
| InfluxDB | 512m | 217m | 58% |
| Grafana | 384m | 213m | 45% |
| Loki | 384m | 87m | 77% |
| Tempo | 256m | 138m | 46% |
| Suricata | 256m | 73m | 71% |
