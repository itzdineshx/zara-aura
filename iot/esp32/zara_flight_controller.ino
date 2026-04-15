#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#if __has_include(<esp_arduino_version.h>)
#include <esp_arduino_version.h>
#endif

// WiFi credentials
const char* WIFI_SSID = "Zayma";
const char* WIFI_PASSWORD = "reddragon";

// MQTT broker (HiveMQ Cloud)
const char* MQTT_HOST = "e5c35c674acb4ec6bdb8514fa465cfa6.s1.eu.hivemq.cloud";
const uint16_t MQTT_PORT = 8883;
const char* MQTT_USER = "Zayma";
const char* MQTT_PASSWORD = "Reddragon123";
const char* TOPIC_CONTROL = "zara/flight/control";
const char* TOPIC_STATUS = "zara/flight/status";

// Set true when using a cloud broker on TLS port (usually 8883).
const bool MQTT_USE_TLS = true;

// Paste the broker root CA PEM when available. Leave empty to fallback to insecure TLS mode.
const char* MQTT_ROOT_CA = "";

#ifndef LED_BUILTIN
#define LED_BUILTIN 2
#endif

// BLDC motor (ESC signal on GPIO5)
constexpr uint8_t BLDC_SIGNAL_PIN = 5;
constexpr uint8_t ENGINE_PWM_CHANNEL = 1;
constexpr uint16_t ENGINE_PWM_FREQUENCY_HZ = 50;
constexpr uint8_t ENGINE_PWM_RESOLUTION_BITS = 16;
constexpr uint16_t ESC_MIN_US = 1000;
constexpr uint16_t ESC_MAX_US = 2000;
constexpr uint16_t ESC_STOP_US = ESC_MIN_US;
constexpr uint16_t ESC_SPIN_US = 1300;
constexpr uint16_t ESC_START_BOOST_US = 1450;
constexpr uint16_t ESC_START_BOOST_MS = 350;
constexpr uint16_t ESC_ARM_DELAY_MS = 2500;

WiFiClient wifiClient;
WiFiClientSecure secureClient;
PubSubClient mqttClient;

bool ledOn = false;
bool engineOn = false;
bool enginePwmReady = false;
uint16_t enginePulseUs = ESC_STOP_US;
bool wifiConnectionLogged = false;
bool mqttConnectionLogged = false;
char mqttClientId[40] = {0};

unsigned long lastWifiAttemptMs = 0;
unsigned long lastMqttAttemptMs = 0;

void publishStatus(const char* status) {
  StaticJsonDocument<256> doc;
  doc["status"] = status;
  doc["led_on"] = ledOn;
  doc["engine_on"] = engineOn;
  doc["engine_signal_us"] = enginePulseUs;
  doc["uptime_ms"] = millis();

  char payload[256];
  const size_t len = serializeJson(doc, payload, sizeof(payload));
  mqttClient.publish(TOPIC_STATUS, reinterpret_cast<const uint8_t*>(payload), static_cast<unsigned int>(len), false);
}

uint32_t escPulseUsToDuty(uint16_t pulseUs) {
  const uint32_t pwmPeriodUs = 1000000UL / ENGINE_PWM_FREQUENCY_HZ;
  const uint32_t maxDuty = (1UL << ENGINE_PWM_RESOLUTION_BITS) - 1UL;
  return static_cast<uint32_t>((static_cast<uint64_t>(pulseUs) * maxDuty) / pwmPeriodUs);
}

uint16_t clampEscPulseUs(int pulseUs) {
  if (pulseUs < static_cast<int>(ESC_MIN_US)) {
    return ESC_MIN_US;
  }
  if (pulseUs > static_cast<int>(ESC_MAX_US)) {
    return ESC_MAX_US;
  }
  return static_cast<uint16_t>(pulseUs);
}

void initEnginePwm() {
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  enginePwmReady = ledcAttach(BLDC_SIGNAL_PIN, ENGINE_PWM_FREQUENCY_HZ, ENGINE_PWM_RESOLUTION_BITS);
#else
  ledcSetup(ENGINE_PWM_CHANNEL, ENGINE_PWM_FREQUENCY_HZ, ENGINE_PWM_RESOLUTION_BITS);
  ledcAttachPin(BLDC_SIGNAL_PIN, ENGINE_PWM_CHANNEL);
  enginePwmReady = true;
#endif
}

void writeEscPulseUs(uint16_t pulseUs) {
  if (!enginePwmReady) {
    return;
  }

  const uint16_t clampedPulseUs = clampEscPulseUs(pulseUs);
  const uint32_t duty = escPulseUsToDuty(clampedPulseUs);
#if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  ledcWrite(BLDC_SIGNAL_PIN, duty);
#else
  ledcWrite(ENGINE_PWM_CHANNEL, duty);
#endif
}

void setEngineState(bool enabled, int requestedPulseUs = -1) {
  if (!enabled) {
    engineOn = false;
    enginePulseUs = ESC_STOP_US;
    writeEscPulseUs(enginePulseUs);
    return;
  }

  uint16_t targetPulseUs = ESC_SPIN_US;
  if (requestedPulseUs >= static_cast<int>(ESC_MIN_US) && requestedPulseUs <= static_cast<int>(ESC_MAX_US)) {
    targetPulseUs = static_cast<uint16_t>(requestedPulseUs);
  }

  // Give a short startup boost so BLDC can overcome static friction.
  const uint16_t boostPulseUs = targetPulseUs < ESC_START_BOOST_US ? ESC_START_BOOST_US : targetPulseUs;
  writeEscPulseUs(boostPulseUs);
  delay(ESC_START_BOOST_MS);

  engineOn = true;
  enginePulseUs = targetPulseUs;
  writeEscPulseUs(enginePulseUs);
}

void applyEngineFailsafe(const char* reason) {
  if (!engineOn) {
    return;
  }

  setEngineState(false);
  Serial.print("[ENGINE] FAILSAFE OFF: ");
  Serial.println(reason);
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

bool isTurnOnEngineCommand(const char* raw) {
  String cmd = String(raw);
  cmd.trim();
  cmd.toLowerCase();
  return cmd == "turn on engine" || cmd == "start engine" || cmd == "engine on" || cmd == "turn on motor";
}

bool isTurnOffEngineCommand(const char* raw) {
  String cmd = String(raw);
  cmd.trim();
  cmd.toLowerCase();
  return cmd == "turn off engine" || cmd == "stop engine" || cmd == "engine off" || cmd == "turn off motor";
}

void handleControlMessage(const JsonDocument& doc) {
  const char* action = doc["action"] | "";
  const char* command = doc["command"] | doc["text"] | "";
  const int value = doc["value"] | -1;

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

  if (strcmp(action, "engine_on") == 0 || strcmp(action, "turn_on_engine") == 0 || isTurnOnEngineCommand(command)) {
    setEngineState(true, value);
    Serial.println("[ENGINE] ON (voice command: turn on engine)");
    Serial.print("[ENGINE] Pulse(us): ");
    Serial.println(enginePulseUs);
    publishStatus("engine_on");
    return;
  }

  if (strcmp(action, "engine_off") == 0 || strcmp(action, "turn_off_engine") == 0 || isTurnOffEngineCommand(command)) {
    setEngineState(false);
    Serial.println("[ENGINE] OFF (voice command: turn off engine)");
    publishStatus("engine_off");
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

  applyEngineFailsafe("WiFi disconnected");

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
    applyEngineFailsafe("MQTT unavailable (WiFi down)");
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

  applyEngineFailsafe("MQTT disconnected");

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
    applyEngineFailsafe("MQTT connect failed");
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

  initEnginePwm();
  if (!enginePwmReady) {
    Serial.println("[ENGINE] PWM init failed.");
  }
  setEngineState(false);
  Serial.println("[ENGINE] Arming ESC...");
  delay(ESC_ARM_DELAY_MS);
  Serial.println("[ENGINE] ESC ready.");

  WiFi.setSleep(false);

  if (MQTT_USE_TLS) {
    if (strlen(MQTT_ROOT_CA) > 0) {
      secureClient.setCACert(MQTT_ROOT_CA);
      Serial.println("[MQTT] TLS enabled with CA certificate.");
    } else {
      secureClient.setInsecure();
      Serial.println("[MQTT] TLS enabled in insecure mode (no CA cert configured).");
    }
    mqttClient.setClient(secureClient);
  } else {
    mqttClient.setClient(wifiClient);
    Serial.println("[MQTT] TLS disabled (plain TCP).");
  }

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
      applyEngineFailsafe("MQTT loop disconnected");
    }
  }
}
