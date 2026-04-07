import urllib.request
import json

req1 = urllib.request.Request(
    'http://localhost:2375/containers/suricata-ids/exec',
    b'{\"AttachStdout\":true,\"Tty\":true,\"Cmd\":[\"tail\",\"-n\",\"15\",\"/var/log/suricata/eve.json\"]}',
    {'Content-Type':'application/json'}
)
res1 = urllib.request.urlopen(req1)
exec_id = json.loads(res1.read())['Id']

req2 = urllib.request.Request(
    f'http://localhost:2375/exec/{exec_id}/start',
    b'{\"Detach\":false,\"Tty\":true}',
    {'Content-Type':'application/json'}
)
res2 = urllib.request.urlopen(req2)
out = res2.read().decode('utf-8')
print('=== OUTPUT START ===')
print(repr(out))
print('=== OUTPUT END ===')
