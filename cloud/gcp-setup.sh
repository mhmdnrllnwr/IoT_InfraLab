#!/usr/bin/env bash
# GCP VM provisioning for IoT_InfraLab
# Usage: Edit variables below, then: bash gcp-setup.sh
set -euo pipefail

# === CONFIGURABLE ===
PROJECT_ID="your-gcp-project"
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-2"
VM_NAME="iot-infralab-vm"
BOOT_DISK_SIZE="20GB"
BOOT_DISK_TYPE="pd-ssd"
IMAGE_PROJECT="ubuntu-os-cloud"
IMAGE_FAMILY="ubuntu-2204-lts"
TAG="iot-infralab"

# === FIREWALL RULES ===
echo "Creating firewall rules..."
gcloud compute firewall-rules create "${TAG}-allow-node-red" \
  --project="${PROJECT_ID}" \
  --direction=INGRESS --priority=1000 \
  --network=default --action=ALLOW \
  --rules=tcp:1880 \
  --source-ranges=0.0.0.0/0 \
  --target-tags="${TAG}" \
  --description="Node-RED (1880)" || echo "Rule exists, skipping."

gcloud compute firewall-rules create "${TAG}-allow-grafana" \
  --project="${PROJECT_ID}" \
  --direction=INGRESS --priority=1000 \
  --network=default --action=ALLOW \
  --rules=tcp:3000 \
  --source-ranges=0.0.0.0/0 \
  --target-tags="${TAG}" \
  --description="Grafana (3000)" || echo "Rule exists, skipping."

gcloud compute firewall-rules create "${TAG}-allow-influxdb" \
  --project="${PROJECT_ID}" \
  --direction=INGRESS --priority=1000 \
  --network=default --action=ALLOW \
  --rules=tcp:8086 \
  --source-ranges=0.0.0.0/0 \
  --target-tags="${TAG}" \
  --description="InfluxDB (8086)" || echo "Rule exists, skipping."

# === VM INSTANCE ===
echo "Creating VM instance..."
gcloud compute instances create "${VM_NAME}" \
  --project="${PROJECT_ID}" \
  --zone="${ZONE}" \
  --machine-type="${MACHINE_TYPE}" \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account="$(gcloud iam service-accounts list --project="${PROJECT_ID}" --filter='displayName:Compute Engine default service account' --format='value(email)')" \
  --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol \
  --tags="${TAG}" \
  --create-disk=auto-delete=yes,boot=yes,device-name="${VM_NAME}",image-project="${IMAGE_PROJECT}",image-family="${IMAGE_FAMILY}",mode=rw,size="${BOOT_DISK_SIZE}",type="${BOOT_DISK_TYPE}" \
  --no-shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --reservation-affinity=any

# === INSTALL DOCKER ===
echo "Waiting for VM to be ready for SSH..."
sleep 30

echo "Installing Docker..."
gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --command='bash -s' <<'REMOTE'
  set -euxo pipefail
  sudo apt-get update -qq
  sudo apt-get install -y -qq ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$(whoami)"
RMOTE

# Clone repo and set up project
echo "Cloning IoT_InfraLab..."
gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --command='bash -s' <<'REMOTE_SETUP'
  set -euxo pipefail
  cd ~
  git clone https://github.com/mhmd-nrllnwr/iot-infralab.git IoT_InfraLab
  cd IoT_InfraLab
  cp .env.example .env
  # User must edit .env with secure values before starting
  echo "=== PROJECT CLONED ==="
  echo "NEXT: ssh in, edit .env, then docker compose up -d"
REMOTE_SETUP

echo "=== DONE ==="
echo "VM: ${VM_NAME} (${ZONE})"
IP=$(gcloud compute instances describe "${VM_NAME}" --zone="${ZONE}" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
echo "External IP: ${IP}"
echo ""
echo "Next steps:"
echo "  1. Set IOT_PROJECT_PATH in .env to: /home/ubuntu/IoT_InfraLab"
echo "  2. Edit .env: set GEMINI_API_KEY, INFLUXDB_TOKEN, passwords"
echo "  3. Build and start:"
echo "     docker compose build security-auditor nodered"
echo "     docker compose up -d"
echo "  4. Create InfluxDB buckets: bash scripts/setup-influxdb.sh"
echo "  5. Access UIs at http://${IP}:1880 and http://${IP}:3000"
echo ""
echo "SSH command:  gcloud compute ssh ${VM_NAME} --zone ${ZONE}"
