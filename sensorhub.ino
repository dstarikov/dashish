#include <TinyGPS++.h>

// GPS module connections
static const int RXPin = 0, TXPin = 1;
static const uint32_t GPSBaud = 9600;

// The TinyGPS++ object
TinyGPSPlus gps;

// Sensor pins
const int pressureInput = A0;
const int coolantSensorPin = A1;
const int oilTempSensorPin = A2;

// Sensor variables
float calculatedPressure = 0;
int currentTempF = 0;   // Coolant temperature in Fahrenheit
int currentOilTempF = 0;   // Oil temperature in Fahrenheit

// RPM meter
volatile unsigned long lastPulseMicros = 0;
volatile unsigned long pulsePeriod = 0;
const int pulsePin = 2;  // Change this pin as needed
float rpm = 0;
const int numReadings = 10;
float readings[numReadings];
int readIndex = 0;
float total = 0;
float average = 0;

// Constants for temperature calculation
const int SERIES_RESISTOR = 10000; // 10KΩ resistor
const float BETA = 3950; // Beta value
const float THERMISTOR_NOMINAL = 10000; // Resistance at 25°C
const float TEMPERATURE_NOMINAL = 25; // Nominal temperature (25°C)

unsigned long previousMillis = 0;
const long interval = 50; // Interval in milliseconds (adjust as needed)

void setup() {
  Serial.begin(115200);  // Initialize USB serial communication at high baud rate
  Serial1.begin(GPSBaud);   // Initialize GPS module serial communication (hardware serial)

  // Ensure all analog pins are set up correctly
  pinMode(pressureInput, INPUT);
  pinMode(coolantSensorPin, INPUT);
  pinMode(oilTempSensorPin, INPUT);
  
  // Initialize RPM meter
  pinMode(pulsePin, INPUT);
  attachInterrupt(digitalPinToInterrupt(pulsePin), countPulse, FALLING);
  
  // Initialize readings array
  for (int i = 0; i < numReadings; i++) {
    readings[i] = 0;
  }
}

void loop() {
  unsigned long currentMillis = millis();

  // Read GPS data
  while (Serial1.available() > 0) {
    gps.encode(Serial1.read());
  }

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // Update the sensor values
    calculatedPressure = calculatePressure(analogRead(pressureInput)); // Calculate oil pressure
    currentTempF = readTemperature(coolantSensorPin); // Get coolant temperature
    currentOilTempF = readTemperature(oilTempSensorPin); // Get oil temperature

    // Read GPS speed
    float speedKmh = gps.speed.isValid() ? gps.speed.kmph() : 0;

    // Read RPM data
    noInterrupts();  // Disable interrupts for accuracy
    unsigned long period = pulsePeriod;
    interrupts();  // Enable interrupts
    if (period > 0) {
      rpm = 20000000.0 / period;
    } else {
      rpm = 0;
    }
    total = total - readings[readIndex];
    readings[readIndex] = rpm;
    total = total + readings[readIndex];
    readIndex = readIndex + 1;
    if (readIndex >= numReadings) {
      readIndex = 0;
    }
    average = total / numReadings;

    // Send data over USB serial in JSON format
    Serial.print("{");
    Serial.print("\"Pressure\": ");
    Serial.print(calculatedPressure, 1);  // Print with 1 decimal for precision
    Serial.print(", \"CoolantTemp\": ");
    Serial.print(currentTempF);
    Serial.print(", \"OilTemp\": ");
    Serial.print(currentOilTempF);
    Serial.print(", \"Speed\": ");
    Serial.print(speedKmh, 1);  // Print with 1 decimal for precision
    Serial.print(", \"RPM\": ");
    Serial.print((int)average);
    Serial.println("}");
  }
}

void countPulse() {
  unsigned long currentMicros = micros();
  pulsePeriod = currentMicros - lastPulseMicros;
  lastPulseMicros = currentMicros;
}

float calculatePressure(int adcValue) {
  float voltage = adcValue * (5.0 / 1023.0);
  float pressure = (voltage - 0.5) * (100.0 / (4.5 - 0.5));
  return pressure;
}

float readTemperature(int pin) {
  int adcValue = analogRead(pin); // Read the ADC value
  float resistance = SERIES_RESISTOR / (1023.0 / adcValue - 1); // Calculate the thermistor resistance
  float tempC = calculateTemperature(resistance); // Convert to temperature in Celsius
  float tempF = (tempC * 9.0 / 5.0) + 32.0; // Convert to Fahrenheit
  return round(tempF); // Return the rounded temperature in Fahrenheit
}

float calculateTemperature(float resistance) {
  // Convert the resistance to temperature using the Steinhart-Hart equation
  float steinhart;
  steinhart = resistance / THERMISTOR_NOMINAL; // (R/Ro)
  steinhart = log(steinhart); // ln(R/Ro)
  steinhart /= BETA; // 1/B * ln(R/Ro)
  steinhart += 1.0 / (TEMPERATURE_NOMINAL + 273.15); // + (1/To)
  steinhart = 1.0 / steinhart; // Invert
  steinhart -= 273.15; // Convert to Celsius
  return steinhart;
}
