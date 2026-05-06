import json
import os
import sys
import time

import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_HOST", "127.0.0.1")
PORT = int(os.getenv("MQTT_PORT", "1883"))
CONTROL = "zara/home/control"
STATUS = "zara/home/status"
received = []


def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"MQTT connect failed rc={rc}")
        return
    print("MQTT connected")
    client.subscribe(STATUS, qos=1)
    payload = json.dumps({"action": "light_on", "value": 1, "source": "copilot-test"})
    client.publish(CONTROL, payload=payload, qos=1, retain=False)
    print(f"Published to {CONTROL}: {payload}")


def on_message(client, userdata, msg):
    try:
        text = msg.payload.decode("utf-8", errors="replace")
        print(f"Status message: {text}")
        data = json.loads(text)
        received.append(data)
    except Exception as ex:
        print(f"Status parse error: {ex}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, keepalive=30)
except Exception as ex:
    print(f"Connection error: {ex}")
    sys.exit(2)

client.loop_start()
ok = False
start = time.time()
while time.time() - start < 12:
    for msg in received:
        status = msg.get("status")
        if status in ("light_on", "controller_online", "online"):
            ok = True
            break
    if ok:
        break
    time.sleep(0.2)

client.loop_stop()
client.disconnect()

if ok:
    print("TEST PASS: Received home automation status update")
    sys.exit(0)

print("TEST FAIL: Did not receive expected home status in time")
sys.exit(1)
