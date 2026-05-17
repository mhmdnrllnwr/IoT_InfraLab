#!/usr/bin/env bash
# IoT InfraLab Setup Script (Linux/macOS)
# Run: bash scripts/setup.sh
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "\033[36m=== IoT InfraLab Setup ===\033[0m"
echo ""

# 1. Check prerequisites
echo -e "\033[33m[1/5] Checking prerequisites...\033[0m"

if ! command -v docker &> /dev/null; then
    echo -e "\033[31mERROR: Docker not found. Install Docker from https://docs.docker.com/engine/install/\033[0m"
    exit 1
fi
echo "  OK: $(docker --version)"

if ! docker compose version &> /dev/null; then
    echo -e "\033[31mERROR: docker compose not available. Update Docker to 20.10+.\033[0m"
    exit 1
fi
echo "  OK: $(docker compose version)"

# 2. Create .env from template
echo -e "\033[33m[2/5] Setting up .env...\033[0m"
cd "$PROJECT_ROOT"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  Created .env from .env.example"
        echo -e "  \033[31mWARNING: Edit .env with your GEMINI_API_KEY and secrets!\033[0m"
    else
        echo -e "  \033[31mWARNING: .env.example not found. Create .env manually.\033[0m"
    fi
else
    echo "  .env already exists, skipping."
fi

# 3. Create required directories
echo -e "\033[33m[3/5] Creating required directories...\033[0m"
dirs=(
    "infrastructure/mosquitto/data"
    "infrastructure/mosquitto/log"
    "infrastructure/suricata/run"
    "infrastructure/suricata/logs"
    "infrastructure/influxdb/data"
    "infrastructure/influxdb/config"
    "infrastructure/grafana/data"
    "infrastructure/loki/data"
)
for d in "${dirs[@]}"; do
    if [ ! -d "$d" ]; then
        mkdir -p "$d"
        echo "  Created: $d"
    fi
done
echo "  Done."

# 4. Validate docker compose config
echo -e "\033[33m[4/5] Validating docker compose config...\033[0m"
if docker compose config > /dev/null; then
    echo "  OK: docker-compose.yaml is valid."
else
    echo -e "\033[31m  ERROR: docker compose config failed. Check docker-compose.yaml.\033[0m"
    exit 1
fi

# 5. Next steps
echo -e "\033[32m[5/5] Setup complete!\033[0m"
echo ""
echo -e "\033[36mNext steps:\033[0m"
echo "  1. Edit .env file with your secrets"
echo "     nano .env    # or vim .env"
echo ""
echo "  2. Build custom images"
echo "     docker compose build security-auditor"
echo ""
echo "  3. Start the stack"
echo "     docker compose up -d"
echo ""
echo "  4. Access services"
echo "     Node-RED:  http://localhost:1880"
echo "     Grafana:   http://localhost:3000   (admin / your_password)"
echo "     InfluxDB:  http://localhost:8086"
echo ""
echo "  5. Generate Grafana dashboards (if needed)"
echo "     python gen_dashboards.py"
