import json

with open('src/simulation/nodered/NodeRed_Data/flows.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for n in data:
    if n.get('name') == 'Parse Suricata & Extract IPs':
        n['outputs'] = 3
        soc_node_id = next((x['id'] for x in data if x.get('name') == 'SOC Log View'), None)
        
        n['func'] = '''let raw = msg.payload || '';
let lines = raw.split('\\n');
let alerts = [];
let attackerIPs = new Set();
let newSOCMsgs = [];

let lastAlertTime = flow.get('last_suricata_alert_time') || 0;
let highestTime = lastAlertTime;

for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();
    if (!line) continue;
    let jsonStart = line.indexOf('{"timestamp"');
    if (jsonStart !== -1) {
        try {
            let evt = JSON.parse(line.substring(jsonStart));
            if (evt.event_type === 'alert') {
                let evtTime = new Date(evt.timestamp).getTime();
                let time = new Date(evt.timestamp).toLocaleTimeString();
                let sig = evt.alert.signature;
                let src = evt.src_ip;
                alerts.push(`[${time}] 🚨 DETECTED: ${sig}\\n    Source: ${src}`);
                if (evt.src_ip) attackerIPs.add(evt.src_ip);
                
                if (evtTime > lastAlertTime) {
                    newSOCMsgs.push({ topic: 'system_log', payload: `🚨 SURICATA ALARM: ${sig} (Source: ${src})` });
                    if (evtTime > highestTime) highestTime = evtTime;
                }
            }
        } catch(e) {}
    }
}
flow.set('last_suricata_alert_time', highestTime);

alerts = alerts.reverse().slice(0, 10);

let msgAlerts = { topic: 'suricata_alerts', payload: '' };
if (alerts.length === 0) {
    msgAlerts.payload = '🟢 System Secure: Watching for active threats in eve.json...';
} else {
    msgAlerts.payload = alerts.join('\\n\\n');
}

let msgAttackers = { payload: Array.from(attackerIPs) };

return [msgAlerts, msgAttackers, newSOCMsgs];'''

        while len(n.get('wires', [])) < 3:
            n['wires'].append([])
        
        if soc_node_id and soc_node_id not in n['wires'][2]:
            n['wires'][2].append(soc_node_id)

with open('src/simulation/nodered/NodeRed_Data/flows.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print('Updated successfully')
