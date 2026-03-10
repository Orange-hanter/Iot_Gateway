/*
  Arduino firmware: Button + BPM280 humidity + temperature wrapper

  Notes:
  - Temperature sensor is abstracted via TemperatureSensor class.
  - Current implementation uses a placeholder adapter and can be replaced later.
  - Output is JSON lines over Serial at 115200.
*/

const int BUTTON_PIN = 2;
const unsigned long SEND_INTERVAL_MS = 2000;
const unsigned long BUTTON_DEBOUNCE_MS = 40;

class TemperatureSensor {
public:
  virtual ~TemperatureSensor() {}
  virtual bool begin() = 0;
  virtual bool readCelsius(float &valueOut) = 0;
  virtual const char* className() = 0;
};

class PlaceholderTemperatureSensor : public TemperatureSensor {
public:
  bool begin() override { return true; }

  bool readCelsius(float &valueOut) override {
    // Placeholder implementation until concrete hardware is selected.
    valueOut = NAN;
    return false;
  }

  const char* className() override { return "placeholder"; }
};

class BPM280HumiditySensor {
public:
  bool begin() {
    // Placeholder init. Add real BPM280 init when hardware library is finalized.
    return true;
  }

  bool readHumidity(float &valueOut) {
    // Placeholder value for integration checks.
    // Replace with actual BPM280 humidity reading later.
    valueOut = 50.0;
    return true;
  }
};

PlaceholderTemperatureSensor temperatureSensor;
BPM280HumiditySensor humiditySensor;

unsigned long lastSentAt = 0;
volatile bool buttonEventLatched = false;
volatile unsigned long buttonPressCount = 0;
volatile unsigned long pendingPressEvents = 0;
volatile unsigned long lastButtonInterruptAt = 0;

void onButtonInterrupt() {
  unsigned long now = millis();
  if (now - lastButtonInterruptAt < BUTTON_DEBOUNCE_MS) {
    return;
  }

  lastButtonInterruptAt = now;
  buttonEventLatched = true;
  buttonPressCount++;
  pendingPressEvents++;
}

void sendHandshake() {
  Serial.print("{\"type\":\"handshake\",\"device_id\":\"ARDUINO_BUTTON_BPM280\",\"firmware\":\"1.0.0\",\"sensor\":\"BUTTON_BPM280\",\"temperature_sensor_class\":\"");
  Serial.print(temperatureSensor.className());
  Serial.println("\"}");
}

void sendData(
  int buttonState,
  bool buttonChanged,
  unsigned long pressesSinceLastSend,
  float humidity,
  bool hasHumidity,
  float temperature,
  bool hasTemperature
) {
  int buttonPressed = (buttonState == LOW) ? 1 : 0;

  Serial.print("{\"type\":\"data\",\"sensor\":\"BUTTON_BPM280\",\"button\":");
  Serial.print(buttonPressed);
  Serial.print(",\"button_changed\":");
  Serial.print(buttonChanged ? "true" : "false");
  Serial.print(",\"button_presses\":");
  Serial.print(pressesSinceLastSend);

  if (hasTemperature) {
    Serial.print(",\"temperature\":");
    Serial.print(temperature, 2);
  }

  if (hasHumidity) {
    Serial.print(",\"humidity\":");
    Serial.print(humidity, 2);
  }

  Serial.print(",\"timestamp\":");
  Serial.print(millis());
  Serial.println("}");
}

void sendButtonPressEvent(int buttonState) {
  int buttonPressed = (buttonState == LOW) ? 1 : 0;

  Serial.print("{\"type\":\"data\",\"sensor\":\"BUTTON_BPM280\",\"button\":");
  Serial.print(buttonPressed);
  Serial.print(",\"button_event\":1,\"button_changed\":true,\"button_presses\":1");
  Serial.print(",\"timestamp\":");
  Serial.print(millis());
  Serial.println("}");
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), onButtonInterrupt, FALLING);

  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  temperatureSensor.begin();
  humiditySensor.begin();

  sendHandshake();
  Serial.println("{\"status\":\"ready\"}");
}

void loop() {
  unsigned long now = millis();
  unsigned long eventCount = 0;
  noInterrupts();
  eventCount = pendingPressEvents;
  pendingPressEvents = 0;
  interrupts();

  if (eventCount > 0) {
    int buttonStateNow = digitalRead(BUTTON_PIN);
    for (unsigned long i = 0; i < eventCount; i++) {
      sendButtonPressEvent(buttonStateNow);
    }
  }

  if (now - lastSentAt < SEND_INTERVAL_MS) {
    delay(10);
    return;
  }

  int buttonState = digitalRead(BUTTON_PIN);
  bool buttonChanged = false;
  unsigned long pressesSinceLastSend = 0;

  noInterrupts();
  buttonChanged = buttonEventLatched;
  pressesSinceLastSend = buttonPressCount;
  buttonEventLatched = false;
  buttonPressCount = 0;
  interrupts();

  float humidity = NAN;
  float temperature = NAN;

  bool hasHumidity = humiditySensor.readHumidity(humidity);
  bool hasTemperature = temperatureSensor.readCelsius(temperature);

  sendData(
    buttonState,
    buttonChanged,
    pressesSinceLastSend,
    humidity,
    hasHumidity,
    temperature,
    hasTemperature
  );

  lastSentAt = now;
}
