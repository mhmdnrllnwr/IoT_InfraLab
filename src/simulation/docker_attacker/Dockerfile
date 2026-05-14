FROM python:3.9-alpine

RUN apk add --no-cache curl nmap iproute2 tcpdump

WORKDIR /attacker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mqtt*.py .
CMD ["/bin/sh"]
