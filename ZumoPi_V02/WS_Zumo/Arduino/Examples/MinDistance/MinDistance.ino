/*
  Read a grid (4x4 or 8x8) of distances from the VL53L5CX.
  Print only the minimum distance per column from the two center rows.
  Center rows are defined using: 
    centerRowOffset = (imageWidth / 2) - 1, and centerRowOffset+1.
  For 4x4: centerRowOffset = 4/2 - 1 = 1, so rows 1 & 2.
  For 8x8: centerRowOffset = 8/2 - 1 = 3, so rows 3 & 4.
*/

#include <Wire.h>
#include <SparkFun_VL53L5CX_Library.h> // http://librarymanager/All#SparkFun_VL53L5CX

SparkFun_VL53L5CX myImager;
VL53L5CX_ResultsData measurementData; // Result data class structure

int imageResolution = 0; // Total number of pads (16 for 4x4, 64 for 8x8)
int imageWidth = 0;      // Grid width (4 for 4x4, 8 for 8x8)

// This function updates the minDistance array with the minimum
// distances per column from the two center rows based on the current sensor reading.
void updateMinDistances(int minDistance[]) {
  int centerRowOffset = imageWidth / 2 - 1; // For 4x4: 1; for 8x8: 3
  for (int col = imageWidth - 1; col >= 0; col--) {
    int idx1 = centerRowOffset * imageWidth + col;
    int idx2 = (centerRowOffset + 1) * imageWidth + col;
    int minVal = measurementData.distance_mm[idx1];
    if (measurementData.distance_mm[idx2] < minVal) {
      minVal = measurementData.distance_mm[idx2];
    }
    minDistance[col] = minVal;
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("SparkFun VL53L5CX Imager Example");

  Wire.begin(); // Resets I2C to 100kHz
  Wire.setClock(400000); // Sensor max I2C frequency is 400kHz

  Serial.println("Initializing sensor board. This can take up to 10s. Please wait.");
  if (!myImager.begin()) {
    Serial.println(F("Sensor not found - check your wiring. Freezing"));
    while (1);
  }
  
  // Choose sensor resolution: Uncomment the desired mode.
  // myImager.setResolution(4*4); // For 4x4 mode
  myImager.setResolution(8*8); // For 8x8 mode
  
  imageResolution = myImager.getResolution();
  imageWidth = sqrt(imageResolution); // For 4x4, imageWidth = 4; for 8x8, imageWidth = 8

  myImager.startRanging();
}

void loop() {
  if (myImager.isDataReady()) {
    if (myImager.getRangingData(&measurementData)) { // Read distance data into array
      // Create an array to store the minimum distance for each column.
      // We use a fixed size of 8 since that's the maximum grid width.
      int minDistance[8];
      
      // Update the minDistance array using the sensor reading.
      updateMinDistances(minDistance);
      
      // Print only the min distances per column.
      Serial.print("Min per column (center rows): ");
      for (int col = 0 ; col < imageWidth; col++) {
        Serial.print("\t");
        Serial.print(minDistance[col]);
      }
      Serial.println();
    }
  }
  
  delay(5); // Small delay between polling
}