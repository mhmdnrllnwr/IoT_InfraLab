# Dashboard Generator (gen_dashboards.py)

## Purpose

Python script that programmatically generates all three Grafana dashboard JSON files. Ensures consistency across dashboards and enables easy query updates.

## Script

**Location:** `D:\IoT_InfraLab\gen_dashboards.py`
**Output:** `infrastructure/grafana/provisioning/dashboards/*.json`

### Usage

```powershell
python gen_dashboards.py
```

Generates:
- `iot_sensors.json` — IoT Sensors Overview (UID: `iot-sensors-overview`)
- `platform_health.json` — Platform Health (UID: `platform-health`)
- `security.json` — Security Operations SOC (UID: `security-operations`)

## Architecture

The script uses Python dict-based templates to construct dashboard panels:

```python
# Shared panel templates
STAT_PANEL = {...}
TIMESERIES_PANEL = {...}
TABLE_PANEL = {...}
```

Each dashboard is a dict with:
- `dashboard` key containing title, uid, tags, time range
- `panels` array with panel definitions
- `templating` section with dashboard variables

### Why Programmatic Generation

| Factor | Hand-written JSON | Generated (chosen) |
|--------|------------------|-------------------|
| Consistency | Manual duplication | Shared templates |
| Updates | Edit 3 files | Edit Python, regenerate |
| Version control | Opaque diffs | Clear Python changes |
| Queries | Copy-paste errors | Variable-based queries |

## Output Files

```
infrastructure/grafana/provisioning/dashboards/
├── iot_sensors.json       # 15 panels
├── platform_health.json   # 9 panels
└── security.json          # 11 panels
```

These are auto-provisioned by Grafana at startup via `dashboards.yaml`.

## Customization

To add a new panel:
1. Edit `gen_dashboards.py` — add panel dict to dashboard panels array
2. Re-run `python gen_dashboards.py`
3. Restart Grafana or refresh dashboard provisioner

## Related

- Full dashboard descriptions: [10-grafana-dashboards.md](10-grafana-dashboards.md)
- Verification: [18-testing-verification.md](18-testing-verification.md)
