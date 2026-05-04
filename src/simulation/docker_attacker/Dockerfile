FROM python:3.9-slim
RUN apt-get update && apt-get install -y curl nmap iproute2 tcpdump dsniff hping3 && rm -rf /var/lib/apt/lists/*
WORKDIR /attacker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mqtt*.py .
CMD ["/bin/sh"]
