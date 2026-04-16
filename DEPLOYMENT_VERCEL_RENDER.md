# ZARA AI on Vercel + Render: ESP32 Communication Guide

This explains exactly how your ESP32 will communicate after deployment when:

- Frontend is on Vercel
- Backend is on Render

## Core Idea

ESP32 does not communicate with the frontend directly.

It communicates with an MQTT broker.

Backend communicates with the same MQTT broker.

Frontend only talks to backend APIs.

## End-to-End Flow

1. User speaks in frontend (Vercel).
2. Frontend calls backend API (Render) at `/voice` or `/chat`.
3. Backend detects a Flight Mode action such as `engine_on`.
4. Backend publishes that action to MQTT topic `zara/flight/control`.
5. ESP32 is subscribed to `zara/flight/control`, receives command, executes hardware action.
6. ESP32 publishes status to `zara/flight/status`.
7. Backend reads status topic and exposes it via `GET /flight/status`.

## Required Components for Internet Use

You must have one publicly reachable MQTT broker that both Render and ESP32 can access.

Recommended:

- Managed MQTT broker (HiveMQ Cloud, EMQX Cloud, or CloudAMQP MQTT)

Not recommended for production:

- Home LAN broker only (because Render cannot reach your local network directly)

## What to Configure in Render (Backend)

Set these Render environment variables:

- `OPENROUTER_API_KEY=<your key>`
- `CORS_ORIGINS=https://<your-vercel-domain>`
- `FLIGHT_MQTT_ENABLED=true`
- `FLIGHT_MQTT_HOST=<broker host>`
- `FLIGHT_MQTT_PORT=8883`
- `FLIGHT_MQTT_USERNAME=<broker username>`
- `FLIGHT_MQTT_PASSWORD=<broker password>`
- `FLIGHT_MQTT_TLS_ENABLED=true`
- `FLIGHT_MQTT_TLS_INSECURE=false`

Optional if your broker requires a custom CA path:

- `FLIGHT_MQTT_TLS_CA_CERT=<path inside container>`

Backend code already supports these TLS settings.

Use this template while filling Render envs:

- `backend/.env.render.example`

## What to Configure in Vercel (Frontend)

Set this Vercel env variable:

- `VITE_BACKEND_URL=https://<your-render-backend-domain>`

Then redeploy frontend.

## No-Error Preflight (Run Before Go-Live)

1. Backend Python version pinned to 3.11 on Render:
   - `backend/runtime.txt` exists with `python-3.11.11`.
   - `backend/.python-version` exists with `3.11.11`.
   - In Render dashboard, set Python version to `3.11.11` (do not keep default 3.14+).
2. Render blueprint exists and points to backend root:
   - `render.yaml`.
3. Vercel SPA routing config exists:
   - `vercel.json` rewrite to `/index.html`.
4. Frontend build passes locally:
   - `npm run build`.
5. Backend source compiles locally:
   - `python -m compileall backend/app`.
6. Render envs set (especially MQTT host/port/user/password/TLS).
7. Vercel env set:
   - `VITE_BACKEND_URL=https://<render-backend-domain>`.
8. CORS allows the exact Vercel production domain.
9. Render build should use default backend requirements without Coqui TTS:
   - `backend/requirements-render.txt` (recommended for Render build stability).
   - Optional Coqui install file: `backend/requirements-tts.txt`.

## What to Configure on ESP32

In your sketch, update:

- `MQTT_HOST` to your cloud broker host
- `MQTT_PORT` to `8883` for TLS broker
- `MQTT_USER` and `MQTT_PASSWORD`
- `MQTT_USE_TLS=true`
- `MQTT_ROOT_CA` with your broker CA PEM (recommended)
- Topics must stay:
  - `zara/flight/control`
  - `zara/flight/status`

Important:

- If broker requires TLS (port 8883), ESP32 should use `WiFiClientSecure` and CA certificate.
- If you keep non-TLS `WiFiClient` on public internet, traffic is insecure.

## Communication Diagram

```text
Browser (Vercel)
   -> HTTPS -> Render Backend (FastAPI)
   -> MQTT publish -> Cloud MQTT Broker
   -> MQTT subscribe -> ESP32
ESP32
   -> MQTT status publish -> Cloud MQTT Broker
Render Backend
   -> MQTT subscribe -> Cloud MQTT Broker
   -> HTTPS status API -> Browser (Vercel)
```

## Quick Validation Checklist

1. Backend health works:
   - `GET https://<render-backend>/health`
2. Flight mode ON:
   - `POST https://<render-backend>/flight-mode` with `{ "enabled": true }`
3. Broker connection visible:
   - `GET https://<render-backend>/flight/status` should show `connected: true`
4. Send command:
   - `POST /chat` with text `turn on engine`
5. ESP32 serial shows command received and status publish.

## Common Failure Causes

1. Wrong `CORS_ORIGINS` for Vercel domain.
2. Render backend not connected to MQTT broker (bad host, port, username, password, TLS mismatch).
3. ESP32 still pointing to old local IP broker.
4. Topic mismatch between backend and firmware.
5. Flight Mode left OFF (`/flight-mode` must be enabled).

## Recommended Production Pattern

1. Frontend: Vercel
2. Backend API: Render
3. MQTT: Managed broker (TLS)
4. ESP32: TLS-enabled MQTT client with broker CA

This is the clean and scalable architecture for online Flight Mode control.

## HiveMQ Cloud Complete Setup (Your Live URLs)

Use this section with your current deployment:

- Frontend: `https://zara-aura.vercel.app`
- Backend: `https://zara-the-ai-backend2.onrender.com`

### 1) Create HiveMQ Cloud Credentials

1. Create a HiveMQ Cloud cluster.
2. Copy hostname from Client Connection Details (for example `xxxxxx.s1.eu.hivemq.cloud`).
3. Create username and password.
4. Use MQTT TLS port `8883`.

### 2) Set Render Environment Variables

Set these in Render Dashboard (Service -> Environment):

- `DEFAULT_MODE=online`
- `CORS_ORIGINS=https://zara-aura.vercel.app`
- `FLIGHT_MQTT_ENABLED=true`
- `FLIGHT_MQTT_HOST=<your-hivemq-host>`
- `FLIGHT_MQTT_PORT=8883`
- `FLIGHT_MQTT_CLIENT_ID=zara-backend`
- `FLIGHT_MQTT_USERNAME=<your-hivemq-username>`
- `FLIGHT_MQTT_PASSWORD=<your-hivemq-password>`
- `FLIGHT_MQTT_TLS_ENABLED=true`
- `FLIGHT_MQTT_TLS_INSECURE=false`
- `FLIGHT_MQTT_CONTROL_TOPIC=zara/flight/control`
- `FLIGHT_MQTT_STATUS_TOPIC=zara/flight/status`

Keep build/start commands:

- Build: `pip install -r requirements-render.txt`
- Start: `gunicorn -c gunicorn_conf.py app.main:app`

### 3) Set Vercel Environment Variable

- `VITE_BACKEND_URL=https://zara-the-ai-backend2.onrender.com`

Redeploy frontend after setting env variable.

### 4) Update ESP32 Firmware

In `iot/esp32/zara_flight_controller.ino` set:

- `MQTT_HOST=<your-hivemq-host>`
- `MQTT_PORT=8883`
- `MQTT_USER=<your-hivemq-username>`
- `MQTT_PASSWORD=<your-hivemq-password>`
- `MQTT_USE_TLS=true`

If you have broker CA PEM, set `MQTT_ROOT_CA`; otherwise current code falls back to insecure TLS mode.

### 5) Verify End-to-End

1. Open frontend: `https://zara-aura.vercel.app`
2. Enable Flight Mode in UI.
3. Say or type: `turn on lights`.
4. Check backend status endpoint:

   - `GET https://zara-the-ai-backend2.onrender.com/flight/status`

Expected:

- `connected: true`
- `last_status.status: led_on` after command
