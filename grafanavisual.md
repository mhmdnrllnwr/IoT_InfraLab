Complete IoT Platform Grafana Dashboard Guide

This document serves as the master blueprint for your IoT Platform Health Dashboard. It contains the logic (Flux Queries) and the visual configuration (Grafana JSON) for every panel. You can use this to quickly rebuild your dashboard, backup your configurations, or share your setup.

🟢 Section 1: Host Performance (Top Row)

1a. Host CPU Utilization (Gauge)

Visual: A gauge showing the total active CPU percentage with Green/Orange/Red thresholds.
Description: Monitors the overall system processing strain. High values can indicate the host is struggling to process security logs or is under a heavy simulated attack.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["cpu"] == "cpu-total")
  |> filter(fn: (r) => r["_field"] == "usage_idle")
  |> map(fn: (r) => ({ r with _value: 100.0 - r._value, _field: "Active CPU" }))
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "host_cpu")


Grafana Panel JSON:

{
  "id": 1,
  "title": "Host CPU Utilization",
  "description": "Monitors the overall system processing strain. High values can indicate the host is struggling to process security logs or is under a heavy simulated attack.",
  "type": "gauge",
  "gridPos": { "h": 8, "w": 6, "x": 0, "y": 0 },
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 100,
      "unit": "percent",
      "color": { "mode": "thresholds" },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 75 },
          { "color": "red", "value": 90 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"cpu\")\n  |> filter(fn: (r) => r[\"cpu\"] == \"cpu-total\")\n  |> filter(fn: (r) => r[\"_field\"] == \"usage_idle\")\n  |> map(fn: (r) => ({ r with _value: 100.0 - r._value, _field: \"Active CPU\" }))\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"host_cpu\")"
    }
  ],
  "options": { "reduceOptions": { "calcs": ["lastNotNull"] } }
}


1b. Host CPU History (Line Chart)

Visual: A timeseries chart showing historical CPU trends with a color-coded threshold background.
Description: Provides a historical view of CPU usage. This allows you to correlate system performance spikes with specific events, such as when an 'iot_attacker_node' starts a high-intensity scan.

Query: Same as the Gauge visual above.

Grafana Panel JSON:

{
  "id": 10,
  "title": "Host CPU History",
  "description": "Provides a historical view of CPU usage. This allows you to correlate system performance spikes with specific events, such as when an 'iot_attacker_node' starts a high-intensity scan.",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 12, "x": 0, "y": 8 },
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 100,
      "unit": "percent",
      "displayName": "Total CPU Usage",
      "custom": {
        "drawStyle": "line",
        "fillOpacity": 10,
        "lineInterpolation": "smooth",
        "thresholdsStyle": {
          "mode": "area"
        }
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 75 },
          { "color": "red", "value": 90 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"cpu\")\n  |> filter(fn: (r) => r[\"cpu\"] == \"cpu-total\")\n  |> filter(fn: (r) => r[\"_field\"] == \"usage_idle\")\n  |> map(fn: (r) => ({ r with _value: 100.0 - r._value, _field: \"Active CPU\" }))\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"host_cpu\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "list", "placement": "bottom", "calcs": ["mean", "max"] },
    "tooltip": { "mode": "single" }
  }
}


2a. Host Memory Usage (Gauge)

Visual: Current RAM consumption out of total physical memory.
Description: Real-time check of total system RAM usage. Essential for preventing 'Out of Memory' crashes during high-traffic security simulations.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "mem")
  |> filter(fn: (r) => r["_field"] == "used_percent")
  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)
  |> yield(name: "host_memory")


Grafana Panel JSON:

{
  "id": 2,
  "title": "Host Memory Usage",
  "description": "Real-time check of total system RAM usage. Essential for preventing 'Out of Memory' crashes during high-traffic security simulations.",
  "type": "gauge",
  "gridPos": { "h": 8, "w": 6, "x": 6, "y": 0 },
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 100,
      "unit": "percent",
      "color": { "mode": "thresholds" },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 80 },
          { "color": "red", "value": 90 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"mem\")\n  |> filter(fn: (r) => r[\"_field\"] == \"used_percent\")\n  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)\n  |> yield(name: \"host_memory\")"
    }
  ],
  "options": { "reduceOptions": { "calcs": ["lastNotNull"] } }
}


2b. Host Memory History (Line Chart)

Visual: A timeseries chart showing historical memory trends with a color-coded threshold background.
Description: Tracks RAM trends over time. Helps detect memory leaks or identifying when memory-intensive processes like InfluxDB are under heavy load.

Query: Same as the Gauge visual above.

Grafana Panel JSON:

{
  "id": 20,
  "title": "Host Memory History",
  "description": "Tracks RAM trends over time. Helps detect memory leaks or identifying when memory-intensive processes like InfluxDB are under heavy load.",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 12, "x": 12, "y": 8 },
  "fieldConfig": {
    "defaults": {
      "min": 0,
      "max": 100,
      "unit": "percent",
      "displayName": "Memory Usage",
      "custom": {
        "drawStyle": "line",
        "fillOpacity": 10,
        "lineInterpolation": "smooth",
        "thresholdsStyle": {
          "mode": "area"
        }
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 80 },
          { "color": "red", "value": 90 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"mem\")\n  |> filter(fn: (r) => r[\"_field\"] == \"used_percent\")\n  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)\n  |> yield(name: \"host_memory\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "list", "placement": "bottom", "calcs": ["mean", "max"] },
    "tooltip": { "mode": "single" }
  }
}


3. System Load Average (1m)

Visual: The "pressure" on the OS CPU queue.
Description: Measures system queue pressure. A value higher than the number of CPU cores indicates the OS is overloaded with processes waiting for execution.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "system")
  |> filter(fn: (r) => r["_field"] == "load1")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "load_avg")


Grafana Panel JSON:

{
  "id": 3,
  "title": "System Load Average (1m)",
  "description": "Measures system queue pressure. A value higher than the number of CPU cores indicates the OS is overloaded with processes waiting for execution.",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 6, "x": 12, "y": 0 },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": { "drawStyle": "line", "fillOpacity": 10, "thresholdsStyle": { "mode": "area" } },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 4 },
          { "color": "red", "value": 8 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"system\")\n  |> filter(fn: (r) => r[\"_field\"] == \"load1\")\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"load_avg\")"
    }
  ]
}


🔵 Section 2: Host I/O & Network

4. Host Network Throughput

Visual: Inbound vs Outbound traffic with simplified list legends.
Description: Monitors total host-level network traffic. Crucial for detecting mass data exfiltration or external DoS floods on the server.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "net")
  |> filter(fn: (r) => r["_field"] == "bytes_recv" or r["_field"] == "bytes_sent")
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "host_net")


Grafana Panel JSON:

{
  "id": 4,
  "title": "Host Network Throughput",
  "description": "Monitors total host-level network traffic. Crucial for detecting mass data exfiltration or external DoS floods on the server.",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 6, "x": 18, "y": 0 },
  "fieldConfig": {
    "defaults": {
      "unit": "Bps",
      "displayName": "${__field.name}",
      "custom": { "drawStyle": "line", "fillOpacity": 10 }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"net\")\n  |> filter(fn: (r) => r[\"_field\"] == \"bytes_recv\" or r[\"_field\"] == \"bytes_sent\")\n  |> derivative(unit: 1s, nonNegative: true)\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"host_net\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "list", "placement": "bottom" }
  }
}


5. Host Disk I/O

Visual: Physical disk read/write speeds, filtering out virtual overlays.
Description: Measures physical disk performance. Useful for spotting when logging operations (like Suricata PCAPs or Loki logs) are causing hardware bottlenecks.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "diskio")
  |> filter(fn: (r) => r["_field"] == "read_bytes" or r["_field"] == "write_bytes")
  |> filter(fn: (r) => r["name"] !~ /^loop/)
  |> derivative(unit: 1s, nonNegative: true)
  |> aggregateWindow(every: v.windowPeriod, fn: max, createEmpty: false)
  |> yield(name: "disk_io")


Grafana Panel JSON:

{
  "id": 5,
  "title": "Host Disk I/O",
  "description": "Measures physical disk performance. Useful for spotting when logging operations (like Suricata PCAPs or Loki logs) are causing hardware bottlenecks.",
  "type": "timeseries",
  "gridPos": { "h": 8, "w": 24, "x": 0, "y": 16 },
  "fieldConfig": {
    "defaults": {
      "unit": "Bps",
      "custom": { "drawStyle": "line", "fillOpacity": 10 }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"diskio\")\n  |> filter(fn: (r) => r[\"_field\"] == \"read_bytes\" or r[\"_field\"] == \"write_bytes\")\n  |> filter(fn: (r) => r[\"name\"] !~ /^loop/)\n  |> derivative(unit: 1s, nonNegative: true)\n  |> aggregateWindow(every: v.windowPeriod, fn: max, createEmpty: false)\n  |> yield(name: \"disk_io\")"
    }
  ]
}


🟡 Section 3: Container Metrics

6. Per-Container CPU Usage

Visual: Sorted legend (latest value descending) with colored warning thresholds.
Description: Individual CPU breakdown for all containers. Helps pinpoint which specific service is misbehaving or being targeted by an attack.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "docker_container_cpu")
  |> filter(fn: (r) => r["_field"] == "usage_percent")
  |> group(columns: ["container_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "container_cpu")


Grafana Panel JSON:

{
  "id": 6,
  "title": "Per-Container CPU Usage",
  "description": "Individual CPU breakdown for all containers. Helps pinpoint which specific service is misbehaving or being targeted by an attack.",
  "type": "timeseries",
  "gridPos": { "h": 10, "w": 12, "x": 0, "y": 24 },
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "displayName": "${__field.labels.container_name}",
      "custom": { 
        "drawStyle": "line", 
        "fillOpacity": 5, 
        "lineInterpolation": "smooth",
        "thresholdsStyle": {
          "mode": "area"
        }
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 70 },
          { "color": "red", "value": 85 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"docker_container_cpu\")\n  |> filter(fn: (r) => r[\"_field\"] == \"usage_percent\")\n  |> group(columns: [\"container_name\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"container_cpu\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "table", "calcs": ["lastNotNull"], "sortBy": "lastNotNull", "sortDesc": true },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}


7. Per-Container Memory Usage

Visual: Absolute memory consumption in Megabytes (MB). (Note: Using ID 777 to prevent VizPanel dashboard rendering errors).
Description: Tracks memory allocation for each container in MB. Useful for identifying services that are expanding their memory footprint due to leaks or excessive processing.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "docker_container_mem")
  |> filter(fn: (r) => r["_field"] == "usage")
  |> group(columns: ["container_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: max, createEmpty: false)
  |> yield(name: "container_mem")


Grafana Panel JSON:

{
  "id": 777,
  "title": "Per-Container Memory Usage",
  "description": "Tracks memory allocation for each container in MB. Useful for identifying services that are expanding their memory footprint due to leaks or excessive processing.",
  "type": "timeseries",
  "gridPos": { "h": 10, "w": 12, "x": 12, "y": 24 },
  "fieldConfig": {
    "defaults": {
      "unit": "bytes",
      "displayName": "${__field.labels.container_name}",
      "custom": { 
        "drawStyle": "line", 
        "fillOpacity": 5,
        "lineInterpolation": "smooth",
        "thresholdsStyle": {
          "mode": "area"
        }
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 536870912 },
          { "color": "red", "value": 1073741824 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"docker_container_mem\")\n  |> filter(fn: (r) => r[\"_field\"] == \"usage\")\n  |> group(columns: [\"container_name\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: max, createEmpty: false)\n  |> yield(name: \"container_mem\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "table", "calcs": ["lastNotNull"], "sortBy": "lastNotNull", "sortDesc": true },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}


8. Per-Container Network Usage

Visual: RX (In) and TX (Out) throughput grouped by container with technical labeling.
Description: Visualizes inbound (RX) and outbound (TX) traffic per container. Essential for identifying exactly which service is moving large amounts of data.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "docker_container_net")
  |> filter(fn: (r) => r["_field"] == "rx_bytes" or r["_field"] == "tx_bytes")
  |> derivative(unit: 1s, nonNegative: true)
  |> map(fn: (r) => ({ r with _field: if r._field == "rx_bytes" then "Received (In)" else "Sent (Out)" }))
  |> group(columns: ["container_name", "_field"])
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "container_net")


Grafana Panel JSON:

{
  "id": 8,
  "title": "Per-Container Network Usage",
  "description": "Visualizes inbound (RX) and outbound (TX) traffic per container. Essential for identifying exactly which service is moving large amounts of data.",
  "type": "timeseries",
  "gridPos": { "h": 10, "w": 24, "x": 0, "y": 34 },
  "fieldConfig": {
    "defaults": {
      "unit": "Bps",
      "displayName": "${__field.labels.container_name} - ${__field.name}",
      "custom": { 
        "drawStyle": "line", 
        "fillOpacity": 5,
        "lineInterpolation": "smooth",
        "thresholdsStyle": {
          "mode": "area"
        }
      },
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "orange", "value": 512000 },
          { "color": "red", "value": 1048576 }
        ]
      }
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"docker_container_net\")\n  |> filter(fn: (r) => r[\"_field\"] == \"rx_bytes\" or r[\"_field\"] == \"tx_bytes\")\n  |> derivative(unit: 1s, nonNegative: true)\n  |> map(fn: (r) => ({ r with _field: if r._field == \"rx_bytes\" then \"Received (In)\" else \"Sent (Out)\" }))\n  |> group(columns: [\"container_name\", \"_field\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)\n  |> yield(name: \"container_net\")"
    }
  ],
  "options": {
    "legend": { "displayMode": "table", "calcs": ["lastNotNull"], "sortBy": "lastNotNull", "sortDesc": true },
    "tooltip": { "mode": "multi", "sort": "desc" }
  }
}


🔴 Section 4: Service Health

9. Service Status History

Visual: State timeline showing Green/Red bars tracking individual container uptime status.
Description: Chronological uptime tracker for all containers. Shows exactly when a container went offline (Red) or came back online (Green) during a security incident.

Query:

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_field"] == "container_status")
  |> group(columns: ["container_name"])
  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)
  |> yield(name: "status_history")


Grafana Panel JSON:

{
  "id": 9,
  "title": "Service Status History",
  "description": "Chronological uptime tracker for all containers. Shows exactly when a container went offline (Red) or came back online (Green) during a security incident.",
  "type": "state-timeline",
  "gridPos": { "h": 8, "w": 24, "x": 0, "y": 44 },
  "fieldConfig": {
    "defaults": {
      "mappings": [
        { "type": "value", "options": { "running": { "text": "Online", "color": "green" }, "exited": { "text": "Offline", "color": "red" }, "restarting": { "text": "Restarting", "color": "orange" } } }
      ]
    }
  },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_field\"] == \"container_status\")\n  |> group(columns: [\"container_name\"])\n  |> aggregateWindow(every: v.windowPeriod, fn: last, createEmpty: false)\n  |> yield(name: \"status_history\")"
    }
  ],
  "options": { "mergeValues": true, "showValue": "never" }
}


🟣 Section 5: Alerts & Incident Management

10. Alert Status Feed (Alert List)

Visual: A dedicated list panel showing current alert states (Firing, Pending, Normal).
Description: Provides an at-a-glance view of all active alerts on the system. Use this to see which specific thresholds (CPU, RAM, Disk) are currently in a breached state.

Configuration: 1. In Grafana, click Add Panel -> Alert List.

Under Display options, select Firing and Pending to focus on active issues.

Use this to track the status of the alerts configured on the visuals in Sections 1-3.

11. Incident Investigation Logs (Logs Panel)

Visual: A scrolling log window showing raw system events.
Description: Displays raw log entries from the system. When a CPU or Network threshold is breached, this panel allows you to scroll through logs to find error messages or security alerts from the 'iot_attacker_node'.

Query (Loki/Syslog):

from(bucket: "platform_metrics")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "syslog")
  // Optionally filter for critical severities only
  // |> filter(fn: (r) => r["severity"] == "err" or r["severity"] == "crit")
  |> yield(name: "system_logs")


Grafana Panel JSON:

{
  "id": 11,
  "title": "Incident Investigation Logs",
  "description": "Displays raw log entries from the system. When a CPU or Network threshold is breached, this panel allows you to scroll through logs to find error messages.",
  "type": "logs",
  "gridPos": { "h": 12, "w": 24, "x": 0, "y": 52 },
  "targets": [
    {
      "refId": "A",
      "query": "from(bucket: \"platform_metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"syslog\")\n  |> yield(name: \"system_logs\")"
    }
  ],
  "options": {
    "showTime": true,
    "enableLogDetails": true,
    "sortOrder": "Descending",
    "wrapLogMessage": true
  }
}


12. How to Link Thresholds to Alerts and Logs (Workflow)

To make the visuals actively notify you when thresholds (like > 80% Memory or > 90% CPU) are breached, you must define alert rules directly on the panels.

Step 1: Create the Alert on the Visual

Edit the panel you want to monitor (for example, 2b. Host Memory History).

Go to the Alert tab (the bell icon) inside the panel editor and click Create Alert Rule.

Set your condition to match your visual threshold (e.g., WHEN last() OF query A IS ABOVE 80).

Save the alert and the dashboard.

Step 2: Monitor via the Alert List (Panel 10)
Once saved, the Alert Status Feed panel will automatically detect this new rule. If the memory crosses 80%, the Alert List will switch from "Normal" to "Pending" and then "Firing", turning red to grab your attention.

Step 3: Investigate using the Logs (Panel 11)
When an alert fires, Grafana will automatically draw a vertical dashed line (an Annotation) across all your timeseries charts at that exact moment.

Find the red vertical line on your CPU or Memory graphs.

Click and drag to highlight that specific narrow time range on the graph.

The Incident Investigation Logs panel will instantly filter to show only the raw system logs from that exact minute, allowing you to read the errors and see exactly which container or process caused the spike.