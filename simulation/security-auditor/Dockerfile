FROM python:3.11-slim

# Install nmap binary required by the python library
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auditor.py .

# -u flag for unbuffered logs so you see prints in docker logs immediately
CMD ["python", "-u", "auditor.py"]