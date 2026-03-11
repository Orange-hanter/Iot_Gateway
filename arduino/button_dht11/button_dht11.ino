/*
  Arduino firmware: Button + DHT11 humidity + temperature

  Notes:
  - DHT11 is used as a source for both humidity and temperature.
  - Output is JSON lines over Serial at 115200.
*/

#include <DHT.h>

const int BUTTON_PIN = 2;
const int DHT_PIN = 3;
const int DHT_TYPE = DHT11;
const unsigned long SEND_INTERVAL_MS = 2000;
const unsigned long BUTTON_DEBOUNCE_MS = 40;

DHT dht(DHT_PIN, DHT_TYPE);

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
  Serial.println("{\"type\":\"handshake\",\"device_id\":\"ARDUINO_BUTTON_DHT11\",\"firmware\":\"1.1.0\",\"sensor\":\"BUTTON_DHT11\",\"temperature_sensor_class\":\"dht11\",\"humidity_sensor_type\":\"dht11\"}");
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

  Serial.print("{\"type\":\"data\",\"sensor\":\"BUTTON_DHT11\",\"button\":");
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

  Serial.print("{\"type\":\"data\",\"sensor\":\"BUTTON_DHT11\",\"button\":");
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

  dht.begin();

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

  humidity = dht.readHumidity();
  temperature = dht.readTemperature();

  bool hasHumidity = !isnan(humidity);
  bool hasTemperature = !isnan(temperature);

  if (!hasHumidity || !hasTemperature) {
    Serial.println("{\"status\":\"sensor_read_error\",\"sensor\":\"BUTTON_DHT11\"}");
  }

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
