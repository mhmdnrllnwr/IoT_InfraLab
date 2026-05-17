import urllib.request as req, os

env_path = os.path.join(os.path.dirname(__file__), '.env')
token = None
with open(env_path) as f:
    for line in f:
        if line.startswith('INFLUXDB_TOKEN='):
            token = line.strip().split('=', 1)[1]
            break

host = os.environ.get('INFLUXDB_HOST', 'localhost')
port = os.environ.get('INFLUXDB_PORT', '8086')
org = os.environ.get('INFLUXDB_ORG', 'infralab')
base = f'http://{host}:{port}/api/v2/query?org={org}'
h = {'Authorization': f'Token {token}',
     'Content-Type': 'application/vnd.flux',
     'Accept': 'application/csv'}

def run(q):
    r = req.Request(base, data=q.encode(), headers=h)
    resp = req.urlopen(r, timeout=10)
    return resp.read().decode()

print("=== FIELDS per measurement ===")
ms = ['cpu', 'mem', 'system', 'net', 'docker_container_cpu', 'docker_container_mem', 'docker_container_net']
for m in ms:
    q = f'import "influxdata/influxdb/schema" schema.measurementFieldKeys(bucket: "platform_metrics", measurement: "{m}")'
    csv = run(q)
    fields = [l.strip() for l in csv.strip().split('\n')[1:] if l.strip() and not l.startswith(',result')]
    fset = set()
    for line in fields:
        parts = line.split(',')
        vals = [p for p in parts if p and p != 'result' and p != 'table']
        for v in vals:
            if v and v != '_result':
                fset.add(v)
    # redo simpler
    q2 = f'from(bucket:"platform_metrics") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "{m}") |> limit(n: 20)'
    csv2 = run(q2)
    # parse fields from column headers
    header = csv2.split('\n')[0] if csv2 else ''
    # Find _field column index
    cols = header.split(',')
    field_idx = None
    for i, c in enumerate(cols):
        if c == '_field':
            field_idx = i
            break
    if field_idx:
        field_values = set()
        for line in csv2.strip().split('\n')[1:]:
            parts = line.split(',')
            if len(parts) > field_idx:
                field_values.add(parts[field_idx])
        print(f"  {m}: {', '.join(sorted(field_values))}")
    else:
        print(f"  {m}: (no _field column)")

print("\n=== CONTAINER NAMES ===")
q = 'from(bucket:"platform_metrics") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "docker_container_cpu" and r._field == "usage_percent") |> group(columns: ["container_name"]) |> distinct(column: "container_name") |> limit(n:30)'
csv = run(q)
# parse container_name values
for line in csv.strip().split('\n')[1:]:
    parts = line.split(',')
    if len(parts) > 1:
        print(f"  {parts[-1]}")

print("\n=== NET INTERFACES ===")
q = 'from(bucket:"platform_metrics") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "net") |> limit(n: 30)'
csv = run(q)
header = csv.split('\n')[0]
cols = header.split(',')
for i, c in enumerate(cols):
    if 'interface' in c.lower():
        print(f"  Column index {i}: {c}")

print("\n=== HOST NAME ===")
# host measurement is cpu's host tag
q = 'from(bucket:"platform_metrics") |> range(start: -10m) |> filter(fn: (r) => r._measurement == "cpu") |> keep(columns: ["host"]) |> limit(n: 1)'
csv = run(q)
print(csv[:300])

print("\nDone.")
