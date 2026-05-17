# Configuration Files Reference

## Purpose

Reference for all user-configurable files that control system behavior — environment variables, sensor blueprints, and type definitions.

---

## .env

**Location:** `D:\IoT_InfraLab\.env` (gitignored — contains secrets)

| Variable | Purpose | Example |
|----------|---------|---------|
| `INFLUXDB_TOKEN` | InfluxDB API authentication | Auto-generated on first run |
| `GEMINI_API_KEY` | Google Gemini AI API key | Set to skip AI analysis (degraded mode) |
| `NODE_RED_CREDENTIAL_SECRET` | Encrypts Node-RED flow credentials | Change for security |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin login | Default: `admin123` |

---

## config/sensor_types.json

**Location:** `D:\IoT_InfraLab\config\sensor_types.json`

Defines base value ranges for each measurable type:

```json
{
  "sensor_types": [
    {
      "type": "temperature",
      "unit": "celsius",
      "range": [10, 40]
    },
    {
      "type": "humidity",
      "unit": "percent",
      "range": [30, 90]
    },
    {
      "type": "pressure",
      "unit": "hPa",
      "range": [950, 1050]
    },
    {
      "type": "vibration",
      "unit": "mm/s",
      "range": [0.0, 10.0]
    },
    {
      "type": "power_consumption",
      "unit": "watts",
      "range": [50, 500]
    }
  ]
}
```

Each entry: `type` (identifier), `unit` (display), `range` [min, max] for random generation.

---

## config/sensor_settings.json

**Location:** `D:\IoT_InfraLab\config\sensor_settings.json`

Defines sensor blueprint presets — specific type-to-range mappings with display metadata:

```json
{
  "blueprints": [
    {
      "id": "dht11",
      "name": "DHT11",
      "sensor_types": ["temperature", "humidity"],
      "temperature_range": [20, 30],
      "humidity_range": [40, 60]
    },
    {
      "id": "dht22",
      "name": "DHT22",
      "sensor_types": ["temperature", "humidity"],
      "temperature_range": [15, 35],
      "humidity_range": [30, 70]
    },
    {
      "id": "bmp280",
      "name": "BMP280",
      "sensor_types": ["temperature", "pressure"],
      "temperature_range": [10, 40],
      "pressure_range": [980, 1020]
    },
    {
      "id": "sw-420",
      "name": "SW-420",
      "sensor_types": ["vibration"],
      "vibration_range": [0.0, 5.0]
    },
    {
      "id": "pzem-004t",
      "name": "PZEM-004T",
      "sensor_types": ["power_consumption"],
      "power_consumption_range": [100, 300]
    }
  ]
}
```

Each blueprint: `id` (slug), `name` (display), `sensor_types` (which types), type-specific range overrides.

---

## Node-RED Persistent Configs

**Location:** `D:\IoT_InfraLab\src\simulation\nodered\NodeRed_Data\`

### saved_sensors.json
10 persistent factory profiles combining sensor types with behavior profiles. Examples:
- CNCMILL-001 (temperature, vibration; profile: failing)
- COMP-101 (temperature, vibration, power_consumption; profile: erratic)
- ENV-201 (temperature, humidity, pressure; profile: normal)

### sensors.json
Active sensor registry — updated in real time as sensors are created/deployed/killed via Node-RED.

---

## Related

- Sensor simulation reading these configs: [05-sensor-simulation.md](05-sensor-simulation.md)
- Node-RED sensor lifecycle: [03-nodered-automation.md](03-nodered-automation.md)
