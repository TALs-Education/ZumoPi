#include <Arduino.h>

// ---------------------------------------------------------------------------
//  USER CONFIGURATION
// ---------------------------------------------------------------------------

// The ADC pin on the Zumo RP2040 (GP26 is often A0 in Arduino pin mapping).
// If using a different pin, update accordingly.
const int ADC_PIN = 26;   

// Voltage divider ratio: if your battery is divided by 11 before hitting ADC,
// set this to 11.0. Adjust as needed if you have a different divider.
const float VOLTAGE_DIVIDER_RATIO = 9.2; // compared to multimeter

// ADC reference voltage on RP2040 is 3.3 V by default
const float ADC_REF_VOLTAGE = 3.3;

// The ADC on RP2040 in Arduino defaults to 12-bit (0–4095).
// If you change resolution (e.g. analogReadResolution(16)), update ADC_MAX.
const int ADC_MAX = 4095;

// If you have multiple cells in series, set this to the number of cells.
// For a single 18650 cell, set CELL_COUNT = 1.
const int CELL_COUNT = 1;

// ---------------------------------------------------------------------------
//  LOOKUP TABLE
// ---------------------------------------------------------------------------
//
// This table is an example of typical Li-ion voltages vs. SoC for one cell.
// You can replace these with the values from the table in your image
// or tweak them for your specific 18650 brand.
//
// voltages[i] must correspond to socPercent[i] at the same index.
// They should be in descending order so we can loop from high to low.
//
// For example, 4.20 V -> 100%, 3.00 V -> 0%.
const float voltages[]   = {4.20, 4.10, 4.00, 3.90, 3.80, 3.70, 3.60, 3.50, 3.40, 3.30, 3.20, 3.00};
const int   socPercent[] = { 100,  90,   80,   70,   60,   50,   40,   30,   20,   10,    5,    0 };

// Number of entries in our table
const int NUM_ENTRIES = sizeof(voltages) / sizeof(voltages[0]);

// ---------------------------------------------------------------------------
//  HELPER FUNCTIONS
// ---------------------------------------------------------------------------

// Read battery voltage (in volts) from ADC pin
float readBatteryVoltage() {
  // Perform ADC reading
  int raw = analogRead(ADC_PIN);

  // Convert raw reading to the voltage at the ADC pin
  float voltageAtPin = (float)raw / (float)ADC_MAX * ADC_REF_VOLTAGE;

  // Reverse the voltage divider scaling
  float batteryVoltage = voltageAtPin * VOLTAGE_DIVIDER_RATIO;

  return batteryVoltage;
}

// Return approximate SoC % for a single Li-ion cell
// using the lookup table and linear interpolation
int getSoCFromVoltage(float cellVoltage) {
  // If voltage is above highest table entry, clamp to max
  if (cellVoltage >= voltages[0]) {
    return socPercent[0];
  }
  // If voltage is below lowest table entry, clamp to min
  if (cellVoltage <= voltages[NUM_ENTRIES - 1]) {
    return socPercent[NUM_ENTRIES - 1];
  }

  // Otherwise, do a piecewise linear interpolation
  for (int i = 0; i < NUM_ENTRIES - 1; i++) {
    float vHigh = voltages[i];
    float vLow  = voltages[i + 1];

    if (cellVoltage <= vHigh && cellVoltage > vLow) {
      // The fraction of the way between vHigh and vLow
      float fraction = (cellVoltage - vLow) / (vHigh - vLow);

      // Interpolate the SoC
      float socHigh = socPercent[i];
      float socLow  = socPercent[i + 1];
      float soc = socLow + (socHigh - socLow) * fraction;

      return (int)(soc + 0.5); // Round to nearest integer
    }
  }

  // Fallback (shouldn’t happen if table is consistent)
  return 0;
}

// ---------------------------------------------------------------------------
//  ARDUINO SETUP AND LOOP
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(ADC_PIN, INPUT);
  analogReadResolution(12); 
  
}

void loop() {
  // 1) Read total battery voltage
  float totalVoltage = readBatteryVoltage();

  // 2) Compute per-cell voltage if you have multiple cells in series
  float cellVoltage = totalVoltage / CELL_COUNT;

  // 3) Get SoC from the lookup table
  int soc = getSoCFromVoltage(cellVoltage);

  // Print results
  Serial.print("Battery Voltage: ");
  Serial.print(totalVoltage, 2);
  Serial.print(" V (");
  Serial.print(cellVoltage, 2);
  Serial.print(" V/cell), Estimated SoC: ");
  Serial.print(soc);
  Serial.println("%");

  delay(100);
}
