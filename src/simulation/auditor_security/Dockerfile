FROM python:3.11-alpine

RUN apk add --no-cache nmap

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auditor.py .

# -u flag for unbuffered logs so you see prints in docker logs immediately
CMD ["python", "-u", "auditor.py"]
