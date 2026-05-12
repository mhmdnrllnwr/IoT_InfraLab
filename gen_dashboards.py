import json
import os

# Common Structure
def create_base(title, uid, templating_list, tags=None):
    if tags is None:
        tags = ["infralab"]
    return {
        "title": title,
        "uid": uid,
        "tags": tags,
        "schemaVersion": 39,
        "version": 1,
        "time": { "from": "now-15m", "to": "now" },
        "timepicker": {
            "refresh_intervals": ["5s","10s","30s","1m","5m","15m","30m","1h"]
        },
        "timezone": "browser",
        "editable": True,
        "graphTooltip": 1,
        "templating": { "list": templating_list },
        "panels": []
    }

# 1. IoT Sensors Dashboard
def get_iot_sensors():
    t_list = [
        {"name": "sensor_id", "type": "query", "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "query": "v1.tagValues(bucket:\"sensor_data\", tag:\"sensor_id\")", "includeAll": True, "multi": False, "sort": 1},
        {"name": "sensor_type", "type": "query", "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "query": "v1.tagValues(bucket:\"sensor_data\", tag:\"sensor_type\")", "includeAll": True, "multi": False, "sort": 1},
        {"name": "profile", "type": "query", "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "query": "v1.tagValues(bucket:\"sensor_data\", tag:\"profile\")", "includeAll": True, "multi": False, "sort": 1}
    ]
    dash = create_base("IoT Sensors Overview", "iot-sensors-overview", t_list, ["infralab", "iot", "sensors", "telemetry", "influxdb"])

    panels = [
        # Overview Row
        {"type": "stat", "title": "Active Sensors", "gridPos": {"h": 4, "w": 4, "x": 0, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "options": {"colorMode": "background", "graphMode": "area"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> keep(columns: [\"sensor_id\"]) |> unique() |> count()", "rawQuery": True}]},
        {"type": "stat", "title": "Data Points / min", "gridPos": {"h": 4, "w": 4, "x": 4, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "options": {"colorMode": "value", "reduceOptions": {"calcs": ["rate"]}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> filter(fn: (r) => r.sensor_id == \"${sensor_id}\" or \"${sensor_id}\" == \"$__all\") |> filter(fn: (r) => r.sensor_type == \"${sensor_type}\" or \"${sensor_type}\" == \"$__all\") |> aggregateWindow(every: 1m, fn: count) |> mean()", "rawQuery": True}]},
        {"type": "stat", "title": "Sensors With Dropouts", "gridPos": {"h": 4, "w": 4, "x": 8, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "options": {"colorMode": "background", "graphMode": "none"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> group(columns: [\"sensor_id\"]) |> elapsed() |> filter(fn: (r) => r.elapsed > 30) |> group() |> distinct(column: \"sensor_id\") |> count()", "rawQuery": True}]},
        {"type": "stat", "title": "Current Avg Temperature", "gridPos": {"h": 4, "w": 4, "x": 12, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "celsius"}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> filter(fn: (r) => r.sensor_type == \"temperature\") |> filter(fn: (r) => r.sensor_id == \"${sensor_id}\" or \"${sensor_id}\" == \"$__all\") |> filter(fn: (r) => r.profile == \"${profile}\" or \"${profile}\" == \"$__all\") |> aggregateWindow(every: 30s, fn: mean) |> last()", "rawQuery": True}]},
        {"type": "stat", "title": "Spikes Detected", "gridPos": {"h": 4, "w": 4, "x": 16, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "options": {"colorMode": "background", "reduceOptions": {"calcs": ["count"]}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> filter(fn: (r) => r.profile == \"erratic\") |> filter(fn: (r) => r.sensor_id == \"${sensor_id}\" or \"${sensor_id}\" == \"$__all\") |> map(fn: (r) => ({ r with _value: 1.0 }))", "rawQuery": True}]},
        {"type": "stat", "title": "Failing Sensors Count", "gridPos": {"h": 4, "w": 4, "x": 20, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "options": {"colorMode": "background"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> filter(fn: (r) => r.profile == \"failing\") |> group(columns: [\"sensor_id\"]) |> distinct(column: \"sensor_id\") |> count()", "rawQuery": True}]},
        
        # Per-Sensor Row
        {"type": "timeseries", "title": "Temperature", "gridPos": {"h": 8, "w": 8, "x": 0, "y": 6}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "celsius"}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"temperature\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Vibration", "gridPos": {"h": 8, "w": 8, "x": 8, "y": 6}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"decimals": 2}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"vibration\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Power Draw", "gridPos": {"h": 8, "w": 8, "x": 16, "y": 6}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "watt"}}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"power_draw\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        
        # Sensor-Type Agg Row
        {"type": "timeseries", "title": "Avg Temperature by Sensor", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 15}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"temperature\") |> group(columns: [\"sensor_id\"]) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Avg Vibration by Sensor", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 15}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"vibration\") |> group(columns: [\"sensor_id\"]) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        
        # Profile/Anomaly Row
        {"type": "timeseries", "title": "Profile Comparison (Temperature)", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"temperature\") |> group(columns: [\"profile\"]) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Spike Detection", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"temperature\" and r.profile == \"erratic\")", "rawQuery": True}]},
        {"type": "timeseries", "title": "5-min Rolling Average", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 32}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> aggregateWindow(every: 30s, fn: mean) |> timedMovingAverage(every: 5m, period: 5m)", "rawQuery": True}]},
        
        # Zone Row
        {"type": "table", "title": "Sensors by Zone", "gridPos": {"h": 8, "w": 24, "x": 0, "y": 41}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"sensor_data\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> filter(fn: (r) => r.profile == \"${profile}\" or \"${profile}\" == \"$__all\") |> group(columns: [\"sensor_id\", \"sensor_type\", \"profile\"]) |> aggregateWindow(every: 1m, fn: last) |> pivot(rowKey: [\"_time\", \"sensor_id\", \"profile\"], columnKey: [\"sensor_type\"], valueColumn: \"_value\")", "rawQuery": True}]}
    ]
    dash["panels"] = panels
    return dash

# 2. Platform Health
def get_platform_health():
    t_list = [{"name": "service", "type": "query", "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "query": "v1.tagValues(bucket:\"platform_metrics\", tag:\"container_name\")"}]
    dash = create_base("Platform Health", "platform-health", t_list, ["infralab", "infrastructure", "platform", "metrics", "influxdb"])

    panels = [
        {"type": "timeseries", "title": "Host CPU Utilization", "gridPos": {"h": 8, "w": 8, "x": 0, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "percent"}}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"cpu\" and r._field == \"usage_idle\") |> aggregateWindow(every: v.windowPeriod, fn: mean) |> map(fn: (r) => ({ r with _value: 100.0 - r._value }))", "rawQuery": True}]},
        {"type": "timeseries", "title": "Host Memory Usage", "gridPos": {"h": 8, "w": 8, "x": 8, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "bytes"}}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"mem\" and r._field == \"used\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "System Load Average", "gridPos": {"h": 8, "w": 8, "x": 16, "y": 1}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"system\" and r._field == \"load1\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Host Network Throughput", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 9}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "Bps"}}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"net\" and (r._field == \"bytes_recv\" or r._field == \"bytes_sent\")) |> derivative(unit: 1s, nonNegative: true) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Host Disk I/O", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 9}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "fieldConfig": {"defaults": {"unit": "Bps"}}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"diskio\" and (r._field == \"read_bytes\" or r._field == \"write_bytes\")) |> derivative(unit: 1s, nonNegative: true) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},

        {"type": "timeseries", "title": "Per-Container CPU", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 18}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"docker_container_cpu\" and r._field == \"usage_percent\") |> filter(fn: (r) => r.container_name == \"${service}\" or \"${service}\" == \"$__all\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Per-Container Memory", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 18}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"docker_container_mem\" and r._field == \"usage\") |> filter(fn: (r) => r.container_name == \"${service}\" or \"${service}\" == \"$__all\") |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "timeseries", "title": "Per-Container Network", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 26}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"docker_container_net\" and (r._field == \"rx_bytes\" or r._field == \"tx_bytes\")) |> derivative(unit: 1s, nonNegative: true) |> aggregateWindow(every: v.windowPeriod, fn: mean)", "rawQuery": True}]},
        {"type": "table", "title": "Service Status", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 26}, "datasource": {"type": "influxdb", "uid": "InfluxDB"}, "targets": [{"query": "from(bucket: \"platform_metrics\") |> range(start: v.timeRangeStart, stop: v.timeRangeStop) |> filter(fn: (r) => r._measurement == \"docker_container_mem\" and r._field == \"usage\") |> filter(fn: (r) => r.container_name == \"${service}\" or \"${service}\" == \"$__all\") |> last() |> group(columns: [\"container_name\", \"container_id\"])", "rawQuery": True}]}
    ]
    dash["panels"] = panels
    return dash

# 3. Security SOC
def get_security():
    t_list = [
        {"name": "attack_type", "type": "query", "datasource": {"type": "loki", "uid": "Loki"}, "query": "label_values({job=\"suricata\"} | json | event_type=\"alert\", alert_signature)"},
        {"name": "src_ip", "type": "query", "datasource": {"type": "loki", "uid": "Loki"}, "query": "label_values({job=\"suricata\"} | json | event_type=\"alert\", src_ip)"}
    ]
    dash = create_base("Security Operations (SOC)", "security-operations", t_list, ["infralab", "security", "alerts", "ids-ips", "loki"])

    panels = [
        {"type": "stat", "title": "Total Alerts", "gridPos": {"h": 3, "w": 4, "x": 0, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [$__range])"}]},
        {"type": "stat", "title": "Alert Rate", "gridPos": {"h": 3, "w": 4, "x": 4, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "rate({job=\"suricata\"} | json | event_type=\"alert\" [$__rate_interval])"}]},
        {"type": "stat", "title": "IPS Mode", "gridPos": {"h": 3, "w": 4, "x": 8, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" | alert_severity=\"3\" [$__range])"}]},
        {"type": "stat", "title": "Active MQTT Connections", "gridPos": {"h": 3, "w": 4, "x": 12, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count_over_time({job=\"mosquitto\"} |= \"New connection\" [$__range])"}]},
        {"type": "stat", "title": "Unique Attackers", "gridPos": {"h": 3, "w": 4, "x": 16, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count(count by(src_ip) (count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [$__range])))"}]},
        {"type": "stat", "title": "Severity 1", "gridPos": {"h": 3, "w": 4, "x": 20, "y": 1}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" | alert_severity=\"1\" [$__range])"}]},
        
        {"type": "timeseries", "title": "Alert Timeline", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 5}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "sum by(alert_severity) (count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [$__interval]))"}]},
        {"type": "piechart", "title": "Alert Severity Breakdown", "gridPos": {"h": 8, "w": 6, "x": 12, "y": 5}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" | alert_severity=\"1\" [$__range])", "legendFormat": "critical (1)"}, {"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" | alert_severity=\"2\" [$__range])", "legendFormat": "high (2)"}, {"expr": "count_over_time({job=\"suricata\"} | json | event_type=\"alert\" | alert_severity=\"3\" [$__range])", "legendFormat": "medium (3)"}]},
        {"type": "table", "title": "Top Attacker IPs", "gridPos": {"h": 8, "w": 6, "x": 18, "y": 5}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "sum by(src_ip) (count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [$__range]))"}]},
        
        {"type": "bargauge", "title": "Attack Type Distribution", "gridPos": {"h": 8, "w": 12, "x": 0, "y": 14}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "sum by(alert_category) (count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [$__range]))"}]},
        {"type": "logs", "title": "Recent Alerts", "gridPos": {"h": 8, "w": 12, "x": 12, "y": 14}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "{job=\"suricata\"} | json | event_type=\"alert\" | line_format \"{{.alert_severity}} | {{.src_ip}} -> {{.dest_ip}}:{{.dest_port}} | {{.alert_signature}}\""}]},
        {"type": "logs", "title": "Mosquitto Broker Log", "gridPos": {"h": 8, "w": 24, "x": 0, "y": 23}, "datasource": {"type": "loki", "uid": "Loki"}, "targets": [{"expr": "{job=\"mosquitto\"}"}]}
    ]
    dash["panels"] = panels
    return dash

os.makedirs('infrastructure/grafana/provisioning/dashboards', exist_ok=True)
with open('infrastructure/grafana/provisioning/dashboards/iot_sensors.json', 'w') as f: json.dump(get_iot_sensors(), f, indent=2)
with open('infrastructure/grafana/provisioning/dashboards/platform_health.json', 'w') as f: json.dump(get_platform_health(), f, indent=2)
with open('infrastructure/grafana/provisioning/dashboards/security.json', 'w') as f: json.dump(get_security(), f, indent=2)
