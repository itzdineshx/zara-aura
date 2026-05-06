# ZARA Home Automation MQTT (FastAPI + MQTT + ESP32)

This module provides end-to-end home automation control over MQTT.

## End-to-End Flow

Voice/Text Command -> FastAPI Automation Engine -> MQTT Broker -> ESP32 Controller -> Device Action -> MQTT Status -> Backend `/home/status`

## MQTT Topics

- Control topic: `zara/home/control`
- Status topic: `zara/home/status`

## Backend APIs

- `POST /home-mode`
  - Body: `{ "enabled": true }`
  - Enables/disables home automation command execution.
- `GET /home-mode`
  - Returns current home automation mode state.
- `GET /home/status`
  - Returns broker connection state and latest ESP32 status payload.

## Supported Home Actions

- `light_on`, `light_off`
- `fan_on`, `fan_off`, `fan_speed_up`, `fan_speed_down`
- `ac_on`, `ac_off`, `ac_temp_up`, `ac_temp_down`
- `tv_on`, `tv_off`
- `curtain_open`, `curtain_close`
- `door_lock`, `door_unlock`
- `all_on`, `all_off`
- `scene_good_morning`, `scene_good_night`, `scene_away`, `scene_home`
- `status_check`

Example MQTT payload:

```json
{
  "action": "fan_speed_up",
  "value": 60,
  "source": "zara-backend",
  "ts": "2026-05-06T13:17:00.000000+00:00"
}
```

## Safety Behavior

- Commands are blocked when Home Automation mode is disabled.
- Fan speed values are clamped within configured min/max.
- AC target temperature is clamped within configured min/max.
- MQTT publish uses retry and timeout controls.

## Configuration

Set these in `backend/.env`:

- `HOME_AUTOMATION_DEFAULT=false`
- `HOME_MQTT_ENABLED=true`
- `HOME_MQTT_HOST=127.0.0.1`
- `HOME_MQTT_PORT=1883`
- `HOME_MQTT_CONTROL_TOPIC=zara/home/control`
- `HOME_MQTT_STATUS_TOPIC=zara/home/status`

Optional tuning:

- `HOME_MQTT_RETRY_ATTEMPTS=3`
- `HOME_MQTT_RETRY_DELAY_MS=250`
- `HOME_MQTT_PUBLISH_TIMEOUT_S=1.5`
- `HOME_FAN_SPEED_STEP=10`
- `HOME_FAN_SPEED_MIN=0`
- `HOME_FAN_SPEED_MAX=100`
- `HOME_AC_TEMP_STEP=1`
- `HOME_AC_TEMP_MIN=16`
- `HOME_AC_TEMP_MAX=30`

## ESP32 Firmware

Use one of these sketches:

- `iot/esp32/zara_home_automation_controller.ino` (existing migrated controller)
- `iot/esp32/zara_home_automation_full.ino` (complete home automation action coverage)

Required libraries:

- PubSubClient
- ArduinoJson
- ESP32Servo

## Complete Testing

### 1) Automated backend tests

```powershell
$env:PYTHONPATH='e:/projects/zara-home/backend'
e:/projects/zara-home/.venv/Scripts/python.exe -m pytest e:/projects/zara-home/backend/tests -q
```

### 2) Local broker check

If Mosquitto is not installed locally:

```powershell
docker run --name zara-mqtt -p 1883:1883 -d eclipse-mosquitto
```

Monitor status:

```powershell
mosquitto_sub -h 127.0.0.1 -p 1883 -t zara/home/status -v
```

Publish a manual command:

```powershell
mosquitto_pub -h 127.0.0.1 -p 1883 -t zara/home/control -m '{"action":"light_on","value":1}'
```

### 3) API validation sequence

```powershell
# Enable mode
curl -X POST http://127.0.0.1:8000/home-mode -H "Content-Type: application/json" -d "{\"enabled\":true}"

# Trigger command through NLP route
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"text\":\"turn on lights\",\"mode\":\"smart\"}"

# Inspect broker state
curl http://127.0.0.1:8000/home/status
```
