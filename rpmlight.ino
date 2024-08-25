#include <Adafruit_NeoPixel.h>

// Pin and LED strip configuration
#define LED_PIN    16   // Pin connected to the data line of the LED strip
#define NUM_LEDS   9    // Number of LEDs in the strip

Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// RPM thresholds and their corresponding colors
#define YELLOW_SINGLE_THRESHOLD  5000
#define DARK_YELLOW_THRESHOLD    5600
#define ORANGE_THRESHOLD         5900
#define BLOOD_ORANGE_THRESHOLD   6200
#define RED1_THRESHOLD           6400
#define RED2_THRESHOLD           6500
#define RED3_THRESHOLD           6600
#define BLINK_THRESHOLD          6700  // Threshold for RPM to start blinking

// Button pin configuration
#define BUTTON1_PIN  3   // Button to toggle brightness
#define BUTTON2_PIN  4   // Button to reset LEDs

// Global variables
int brightness = 3;      // Default brightness
bool resetLEDs = false;  // Flag to reset LEDs
bool isBlinking = false; // Flag to indicate if blinking is active
unsigned long lastBlinkTime = 0; // For timing the LED blinking

void setup() {
  Serial.begin(115200);  // Start serial communication with the Raspberry Pi
  strip.begin();
  
  // Run boot-up animation using the defined colors
  bootUpAnimation();

  strip.show();  // Initialize all pixels to 'off'
  
  pinMode(BUTTON1_PIN, INPUT_PULLUP);  // Set button 1 as input with pull-up
  pinMode(BUTTON2_PIN, INPUT_PULLUP);  // Set button 2 as input with pull-up
}

void loop() {
  // Check for button presses
  checkButtons();
  
  if (Serial.available() > 0) {
    // Read the incoming RPM value
    String rpmString = Serial.readStringUntil('\n');
    int rpm = rpmString.toInt();

    // Update the LEDs based on the RPM value if not reset
    if (!resetLEDs) {
      updateLEDs(rpm);
    } else {
      strip.clear();  // Clear LEDs when reset is triggered
      strip.show();
    }
  }

  // If RPM is high enough, make the top 2 red LEDs blink
  if (isBlinking) {
    blinkTopRedLEDs();
  }
}

// Function to update LEDs based on RPM value
void updateLEDs(int rpm) {
  strip.clear();  // Clear the strip before updating

  // Light up LEDs based on RPM thresholds
  if (rpm >= YELLOW_SINGLE_THRESHOLD) {
    setLEDColor(0, 2, 255, 255, 0, brightness);  // First 3 LEDs Yellow
  }
  if (rpm >= ORANGE_THRESHOLD) {
    setLEDColor(3, 4, 255, 165, 0, brightness);  // Next 2 LEDs Orange
  }
  if (rpm >= BLOOD_ORANGE_THRESHOLD) {
    setLEDColor(5, 5, 255, 69, 0, brightness);   // Blood Orange LEDs (dimmer)
  }
  if (rpm >= RED1_THRESHOLD) {
    setLEDColor(6, 6, 255, 0, 0, brightness);    // 1st Red LED (dimmer)
  }
  if (rpm >= RED2_THRESHOLD) {
    setLEDColor(7, 7, 255, 0, 0, brightness);    // 2nd Red LED (dimmer)
  }
  if (rpm >= RED3_THRESHOLD) {
    setLEDColor(8, 8, 255, 0, 0, brightness);    // 3rd Red LED (dimmer)
  }

  // If RPM is above the blink threshold, enable blinking for the top two LEDs
  if (rpm >= BLINK_THRESHOLD) {
    isBlinking = true;
  } else {
    isBlinking = false;
    strip.show();  // Apply the changes to the LED strip
  }
}

// Helper function to set a range of LEDs to a color with dimming
void setLEDColor(int start, int end, uint8_t r, uint8_t g, uint8_t b, uint8_t brightness) {
  r = (r * brightness) / 255;
  g = (g * brightness) / 255;
  b = (b * brightness) / 255;
  for (int i = start; i <= end; i++) {
    strip.setPixelColor(i, strip.Color(r, g, b));
  }
}

// Function to check button states
void checkButtons() {
  // Button 1: Toggle brightness
  if (digitalRead(BUTTON1_PIN) == LOW) {
    brightness = (brightness == 3) ? 255 : 3;  // Toggle between low and high brightness
    delay(200);  // Debounce delay
  }

  // Button 2: Reset LEDs
  if (digitalRead(BUTTON2_PIN) == LOW) {
    resetLEDs = !resetLEDs;  // Toggle reset mode
    delay(200);  // Debounce delay
  }
}

// Function to make the top two red LEDs blink
void blinkTopRedLEDs() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastBlinkTime >= 75) {  // Blink every 75 ms
    static bool ledsOn = false;

    if (ledsOn) {
      // Turn off the top two red LEDs
      strip.setPixelColor(7, strip.Color(0, 0, 0));  // 2nd Red LED
      strip.setPixelColor(8, strip.Color(0, 0, 0));  // 3rd Red LED
    } else {
      // Turn on the top two red LEDs
      strip.setPixelColor(7, strip.Color(255, 0, 0));  // 2nd Red LED
      strip.setPixelColor(8, strip.Color(255, 0, 0));  // 3rd Red LED
    }

    ledsOn = !ledsOn;  // Toggle LED state
    strip.show();  // Update the LED strip
    lastBlinkTime = currentTime;  // Reset the last blink time
  }
}

// Function to create a boot-up animation using the same colors from the RPM thresholds
void bootUpAnimation() {
  // Sweep through each LED and set it to the appropriate color
  setLEDColor(0, 2, 255, 255, 0, brightness);  // Yellow (first 3 LEDs)
  strip.show();
  delay(100);

  setLEDColor(3, 4, 255, 165, 0, brightness);  // Orange (next 2 LEDs)
  strip.show();
  delay(100);

  setLEDColor(5, 5, 255, 69, 0, brightness);   // Blood Orange
  strip.show();
  delay(100);

  setLEDColor(6, 6, 255, 0, 0, brightness);    // Red 1
  strip.show();
  delay(100);

  setLEDColor(7, 7, 255, 0, 0, brightness);    // Red 2
  strip.show();
  delay(100);

  setLEDColor(8, 8, 255, 0, 0, brightness);    // Red 3
  strip.show();
  delay(100);

  // Clear the strip after the animation
  strip.clear();
  strip.show();
}
