import json
import time
import sys
import paho.mqtt.client as mqtt
BROKER = "10.67.9.249"
PORT = 1884
CONTROL = "zara/flight/control"
STATUS = "zara/flight/status"
received = []
def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"MQTT connect failed rc={rc}")
        return
    print("MQTT connected")
    client.subscribe(STATUS, qos=1)
    payload = json.dumps({"command": "turn on lights", "source": "copilot-test"})
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
        if msg.get("status") in ("led_on", "controller_online") and msg.get("led_on") is True:
            ok = True
            break
    if ok:
        break
    time.sleep(0.2)
client.loop_stop()
client.disconnect()
if ok:
    print("TEST PASS: Received status confirming led_on=true")
    sys.exit(0)
print("TEST FAIL: Did not receive led_on=true status in time")
sys.exit(1)
