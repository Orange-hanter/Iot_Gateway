/*
 * Arduino Mega + MQ2 Gas Sensor
 * 
 * Прошивка для отправки данных с датчика MQ2 через Serial порт
 * Формат данных: JSON
 * 
 * Подключение MQ2:
 * - VCC -> 5V
 * - GND -> GND
 * - A0 (Analog) -> A0 на Arduino
 * - D0 (Digital) -> Pin 2 на Arduino (опционально)
 * 
 * Скорость: 115200 baud
 */

#define MQ2_ANALOG_PIN A0
#define MQ2_DIGITAL_PIN 2
#define LED_PIN 13

// Интервал отправки данных (мс)
const unsigned long SEND_INTERVAL = 2000;
unsigned long lastSendTime = 0;

// Параметры калибровки MQ2
const float RL_VALUE = 5.0;         // Load resistance (kOhm)
const float RO_CLEAN_AIR = 9.83;    // Sensor resistance in clean air

// Уникальный идентификатор устройства
const char* DEVICE_ID = "ARDUINO_MQ2";
const char* FIRMWARE_VERSION = "1.0.0";

void setup() {
  // Инициализация Serial порта
  Serial.begin(115200);
  
  // Настройка пинов
  pinMode(MQ2_ANALOG_PIN, INPUT);
  pinMode(MQ2_DIGITAL_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  
  // Сигнал готовности
  blinkLED(3);
  
  // Отправка приветственного сообщения
  sendHandshake();
  
  // Прогрев датчика (MQ2 требует 20-30 секунд)
  Serial.println("{\"status\":\"warming_up\",\"duration_sec\":30}");
  delay(30000);
  Serial.println("{\"status\":\"ready\"}");
}

void loop() {
  // Проверка команд от компьютера
  if (Serial.available() > 0) {
    handleCommand();
  }
  
  // Отправка данных с интервалом
  unsigned long currentTime = millis();
  if (currentTime - lastSendTime >= SEND_INTERVAL) {
    sendSensorData();
    lastSendTime = currentTime;
  }
}

void sendHandshake() {
  Serial.print("{\"type\":\"handshake\",\"device_id\":\"");
  Serial.print(DEVICE_ID);
  Serial.print("\",\"firmware\":\"");
  Serial.print(FIRMWARE_VERSION);
  Serial.println("\",\"sensor\":\"MQ2\"}");
}

void sendSensorData() {
  // Чтение аналогового значения
  int analogValue = analogRead(MQ2_ANALOG_PIN);
  
  // Чтение цифрового значения (HIGH если концентрация превышена)
  int digitalValue = digitalRead(MQ2_DIGITAL_PIN);
  
  // Расчет напряжения
  float voltage = analogValue * (5.0 / 1023.0);
  
  // Расчет сопротивления датчика (Rs)
  float rs = ((5.0 * RL_VALUE) / voltage) - RL_VALUE;
  
  // Расчет отношения Rs/R0
  float ratio = rs / RO_CLEAN_AIR;
  
  // Примерный расчет концентрации газа в PPM
  // Формула для MQ2: PPM = 613.9 * ratio^(-2.074)
  float ppm = 613.9 * pow(ratio, -2.074);
  
  // Отправка данных в JSON формате
  Serial.print("{\"type\":\"data\",\"sensor\":\"MQ2\",");
  Serial.print("\"analog\":");
  Serial.print(analogValue);
  Serial.print(",\"digital\":");
  Serial.print(digitalValue);
  Serial.print(",\"voltage\":");
  Serial.print(voltage, 3);
  Serial.print(",\"resistance\":");
  Serial.print(rs, 2);
  Serial.print(",\"ratio\":");
  Serial.print(ratio, 3);
  Serial.print(",\"ppm\":");
  Serial.print(ppm, 2);
  Serial.print(",\"alert\":");
  Serial.print(digitalValue == HIGH ? "true" : "false");
  Serial.print(",\"timestamp\":");
  Serial.print(millis());
  Serial.println("}");
  
  // Мигание LED при отправке
  digitalWrite(LED_PIN, HIGH);
  delay(50);
  digitalWrite(LED_PIN, LOW);
}

void handleCommand() {
  String command = Serial.readStringUntil('\n');
  command.trim();
  
  if (command == "PING") {
    Serial.println("{\"response\":\"PONG\"}");
  }
  else if (command == "INFO") {
    sendHandshake();
  }
  else if (command == "READ") {
    sendSensorData();
  }
  else if (command == "LED_ON") {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("{\"response\":\"LED_ON\"}");
  }
  else if (command == "LED_OFF") {
    digitalWrite(LED_PIN, LOW);
    Serial.println("{\"response\":\"LED_OFF\"}");
  }
  else {
    Serial.print("{\"error\":\"Unknown command: ");
    Serial.print(command);
    Serial.println("\"}");
  }
}

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}
