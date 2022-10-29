# Edge Service MQTT

## Setup Virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install Dependencies

```bash
pip3 install -r requirements.txt
```

## Start Locally

```bash
python3 main.py <broker_url> <broker_port> <topic> <response_topic>
```

## Build and Run Docker Container

```bash
docker build -t dev.local/edge-service-mqtt:0.1 .
docker compose up -d
```

```
docker run \
    --detach \
    --publish 8080:8080 \
    --name edge-service \
    --rm \
    dev.local/edge-service:0.1
```
