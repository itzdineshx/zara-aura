#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// WiFi credentials
const char* WIFI_SSID = "Zayma";
const char* WIFI_PASSWORD = "reddragon";

// MQTT broker (local Mosquitto)
const char* MQTT_HOST = "10.67.9.51";
const uint16_t MQTT_PORT = 1884;
const char* MQTT_USER = "";
const char* MQTT_PASSWORD = "";
const char* TOPIC_CONTROL = "zara/flight/control";
const char* TOPIC_STATUS = "zara/flight/status";

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

bool ledOn = false;
bool wifiConnectionLogged = false;
bool mqttConnectionLogged = false;
char mqttClientId[40] = {0};

unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;

void publishStatus(const char* status) {
  StaticJsonDocument<256> doc;
  doc["status"] = status;
  doc["led_on"] = ledOn;
  doc["uptime_ms"] = millis();

  char payload[256];
  const size_t len = serializeJson(doc, payload, sizeof(payload));
  mqttClient.publish(TOPIC_STATUS, reinterpret_cast<const uint8_t*>(payload), static_cast<unsigned int>(len), false);
}

bool isTurnOnLightsCommand(const char* raw) {
  String cmd = String(raw);
  cmd.trim();
  cmd.toLowerCase();
  return cmd == "turn on lights" || cmd == "turn on light" || cmd == "start light";
}

bool isTurnOffLightsCommand(const char* raw) {
  String cmd = String(raw);
  cmd.trim();
  cmd.toLowerCase();
  return cmd == "turn off lights" || cmd == "turn off light" || cmd == "stop light";
}

void handleControlMessage(const JsonDocument& doc) {
  const char* action = doc["action"] | "";
  const char* command = doc["command"] | doc["text"] | "";

  if (strcmp(action, "led_on") == 0 || strcmp(action, "turn_on_lights") == 0 || isTurnOnLightsCommand(command)) {
    ledOn = true;
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println("[LED] ON (voice command: turn on lights)");
    publishStatus("led_on");
    return;
  }

  if (strcmp(action, "led_off") == 0 || strcmp(action, "turn_off_lights") == 0 || isTurnOffLightsCommand(command)) {
    ledOn = false;
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("[LED] OFF (voice command: turn off lights)");
    publishStatus("led_off");
    return;
  }

  publishStatus("ignored_command");
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, TOPIC_CONTROL) != 0) {
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);

  if (error) {
    publishStatus("invalid_json");
    return;
  }

  handleControlMessage(doc);
}

void ensureWifiConnected() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiConnectionLogged) {
      Serial.print("[WiFi] Connected. IP: ");
      Serial.println(WiFi.localIP());
      wifiConnectionLogged = true;
    }
    return;
  }

  if (wifiConnectionLogged) {
    Serial.println("[WiFi] Disconnected.");
    wifiConnectionLogged = false;
  }

  const unsigned long now = millis();
  if (now - lastWifiAttemptMs < 5000) {
    return;
  }

  lastWifiAttemptMs = now;
  WiFi.mode(WIFI_STA);
  Serial.println("[WiFi] Connecting...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void ensureMqttConnected() {
  if (WiFi.status() != WL_CONNECTED) {
    if (mqttConnectionLogged) {
      Serial.println("[MQTT] Disconnected (WiFi unavailable).");
      mqttConnectionLogged = false;
    }
    return;
  }

  if (mqttClient.connected()) {
    if (!mqttConnectionLogged) {
      Serial.print("[MQTT] Connected to ");
      Serial.print(MQTT_HOST);
      Serial.print(":");
      Serial.println(MQTT_PORT);
      mqttConnectionLogged = true;
    }
    return;
  }

  if (mqttConnectionLogged) {
    Serial.println("[MQTT] Disconnected.");
    mqttConnectionLogged = false;
  }

  const unsigned long now = millis();
  if (now - lastMqttAttemptMs < 2000) {
    return;
  }

  lastMqttAttemptMs = now;

  const bool connected = (strlen(MQTT_USER) > 0)
    ? mqttClient.connect(mqttClientId, MQTT_USER, MQTT_PASSWORD)
    : mqttClient.connect(mqttClientId);

  if (!connected) {
    Serial.print("[MQTT] Connect failed, state=");
    Serial.println(mqttClient.state());
    return;
  }

  mqttClient.subscribe(TOPIC_CONTROL, 1);
  Serial.print("[MQTT] Connected to ");
  Serial.print(MQTT_HOST);
  Serial.print(":");
  Serial.println(MQTT_PORT);
  mqttConnectionLogged = true;
  publishStatus("controller_online");
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("[BOOT] LED voice controller starting...");

  const uint64_t chipId = ESP.getEfuseMac();
  snprintf(mqttClientId, sizeof(mqttClientId), "zara-esp32-%04X", static_cast<unsigned int>(chipId & 0xFFFF));
  Serial.print("[MQTT] Client ID: ");
  Serial.println(mqttClientId);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  ledOn = false;

  WiFi.setSleep(false);
  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setBufferSize(512);

  ensureWifiConnected();
}

void loop() {
  ensureWifiConnected();
  ensureMqttConnected();

  if (mqttClient.connected()) {
    if (!mqttClient.loop()) {
      Serial.print("[MQTT] Loop lost connection, state=");
      Serial.println(mqttClient.state());
      mqttClient.disconnect();
      mqttConnectionLogged = false;
    }
  }
}
