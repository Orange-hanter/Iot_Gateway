/*
  Arduino firmware: Button + DHT11 humidity + DS18B20 temperature

  Notes:
  - DHT11 is used for humidity.
  - DS18B20 is used as the primary temperature source.
  - Output is JSON lines over Serial at 115200.
*/

#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

const int BUTTON_PIN = 2;
const int DHT_PIN = 3;
const int DS18B20_PIN = 4;
const int DHT_TYPE = DHT11;
const unsigned long SEND_INTERVAL_MS = 2000;
const unsigned long BUTTON_DEBOUNCE_MS = 40;

DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);

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
  Serial.println("{\"type\":\"handshake\",\"device_id\":\"ARDUINO_BUTTON_DHT11\",\"firmware\":\"1.2.0\",\"sensor\":\"BUTTON_DHT11\",\"temperature_sensor_class\":\"ds18b20\",\"humidity_sensor_type\":\"dht11\"}");
}

void sendData(
  int buttonState,
  bool buttonChanged,
  unsigned long pressesSinceLastSend,
  float humidity,
  bool hasHumidity,
  float primaryTemperature,
  bool hasPrimaryTemperature,
  float dht11Temperature,
  bool hasDht11Temperature,
  bool ds18b20Ok
) {
  int buttonPressed = (buttonState == LOW) ? 1 : 0;

  Serial.print("{\"type\":\"data\",\"sensor\":\"BUTTON_DHT11\",\"button\":");
  Serial.print(buttonPressed);
  Serial.print(",\"button_changed\":");
  Serial.print(buttonChanged ? "true" : "false");
  Serial.print(",\"button_presses\":");
  Serial.print(pressesSinceLastSend);

  if (hasPrimaryTemperature) {
    Serial.print(",\"temperature\":");
    Serial.print(primaryTemperature, 2);
  }

  if (hasPrimaryTemperature) {
    Serial.print(",\"ds18b20_temperature\":");
    Serial.print(primaryTemperature, 2);
  }

  if (hasDht11Temperature) {
    Serial.print(",\"dht11_temperature\":");
    Serial.print(dht11Temperature, 2);
  }

  if (hasHumidity) {
    Serial.print(",\"humidity\":");
    Serial.print(humidity, 2);
  }

  Serial.print(",\"ds18b20_ok\":");
  Serial.print(ds18b20Ok ? "true" : "false");

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
  ds18b20.begin();

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
  float dht11Temperature = NAN;
  float ds18b20Temperature = NAN;

  humidity = dht.readHumidity();
  dht11Temperature = dht.readTemperature();

  ds18b20.requestTemperatures();
  ds18b20Temperature = ds18b20.getTempCByIndex(0);

  bool hasHumidity = !isnan(humidity);
  bool hasDht11Temperature = !isnan(dht11Temperature);
  bool hasDs18b20Temperature = ds18b20Temperature > -100.0 && ds18b20Temperature < 125.0;

  float primaryTemperature = hasDs18b20Temperature ? ds18b20Temperature : dht11Temperature;
  bool hasPrimaryTemperature = hasDs18b20Temperature || hasDht11Temperature;

  if (!hasHumidity || !hasPrimaryTemperature) {
    Serial.println("{\"status\":\"sensor_read_error\",\"sensor\":\"BUTTON_DHT11\"}");
  }

  sendData(
    buttonState,
    buttonChanged,
    pressesSinceLastSend,
    humidity,
    hasHumidity,
    primaryTemperature,
    hasPrimaryTemperature,
    dht11Temperature,
    hasDht11Temperature,
    hasDs18b20Temperature
  );

  lastSentAt = now;
}
