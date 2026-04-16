# ZARA AI Online Hosting (Frontend + Backend + Flight Mode)

This guide deploys ZARA AI to a VPS with HTTPS and online Flight Mode control.

## What You Get

- Public frontend over HTTPS
- Public backend API over HTTPS
- MQTT bridge from backend to ESP32 for Flight Mode commands
- Optional self-hosted Mosquitto broker

## 1) Prerequisites

- Ubuntu VPS (recommended: 2 vCPU, 4 GB RAM)
- Domain names:
  - `zara.example.com` (frontend)
  - `api.zara.example.com` (backend)
- Docker + Docker Compose plugin installed
- Open ports on VPS firewall: `80`, `443`

## 2) Clone and Prepare Environment

```bash
git clone https://github.com/itzdineshx/zara-aura.git
cd zara-aura
cp deploy/.env.online.example deploy/.env.online
cp backend/.env.example backend/.env
```

Edit `deploy/.env.online`:

- Set `FRONTEND_DOMAIN`
- Set `API_DOMAIN`
- Set `VITE_BACKEND_URL`
- Set `CORS_ORIGINS`
- Set MQTT values (`FLIGHT_MQTT_*`)

Edit `backend/.env`:

- Set `OPENROUTER_API_KEY`
- Keep any AI model overrides you need

## 3) Option A (Recommended): Managed MQTT Broker

Use a managed broker (for example HiveMQ Cloud) so both backend and ESP32 can connect from anywhere without exposing your own broker port.

In `deploy/.env.online`:

- `FLIGHT_MQTT_HOST=<your-cloud-broker-host>`
- `FLIGHT_MQTT_PORT=8883`
- `FLIGHT_MQTT_USERNAME=<broker-username>`
- `FLIGHT_MQTT_PASSWORD=<broker-password>`
- `FLIGHT_MQTT_TLS_ENABLED=true`
- `FLIGHT_MQTT_TLS_INSECURE=false`

Start stack:

```bash
docker compose --env-file deploy/.env.online -f docker-compose.online.yml up -d --build
```

## 4) Option B: Self-Hosted Mosquitto on the VPS

Create broker password file:

```bash
docker run --rm -it -v "$(pwd)/deploy/mosquitto:/mosquitto" eclipse-mosquitto:2 mosquitto_passwd -c /mosquitto/passwd zara
```

Set in `deploy/.env.online`:

- `FLIGHT_MQTT_HOST=mosquitto`
- `FLIGHT_MQTT_PORT=1883`
- `FLIGHT_MQTT_USERNAME=zara`
- `FLIGHT_MQTT_PASSWORD=<same-password-you-entered>`
- `FLIGHT_MQTT_TLS_ENABLED=false`

Start stack with MQTT profile:

```bash
docker compose --env-file deploy/.env.online -f docker-compose.online.yml --profile selfhosted-mqtt up -d --build
```

## 5) DNS Setup

Create these DNS A records pointing to your VPS public IP:

- `zara.example.com`
- `api.zara.example.com`

Caddy will automatically issue and renew TLS certificates.

## 6) ESP32 Online Flight Mode Settings

Update your firmware MQTT constants to match the broker you selected:

- `MQTT_HOST`
- `MQTT_PORT`
- `MQTT_USER`
- `MQTT_PASSWORD`

Keep topic names consistent with backend env:

- `zara/flight/control`
- `zara/flight/status`

For managed TLS brokers, use `WiFiClientSecure` in the ESP32 sketch and load the broker CA certificate.

## 7) Verify Production

Check service status:

```bash
docker compose --env-file deploy/.env.online -f docker-compose.online.yml ps
```

Backend health:

```bash
curl https://api.zara.example.com/health
```

Flight mode status:

```bash
curl https://api.zara.example.com/flight/status
```

## 8) Safety Recommendations (Important)

- Keep Flight Mode default off (`FLIGHT_MODE_DEFAULT=false`).
- Use strong MQTT credentials and rotate periodically.
- Prefer TLS MQTT for internet control.
- Never arm engine at boot on an attached propeller.
- Add a hardware kill switch for motor power.

## 9) Updates

Pull new code and redeploy:

```bash
git pull
docker compose --env-file deploy/.env.online -f docker-compose.online.yml up -d --build
```
