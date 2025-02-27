#include <Arduino.h>
#include <Pololu3piPlus2040.h>
#include "MelodyPlayer.h"

// Create a ButtonA instance.
ButtonA buttonA;

#define BUZZER_PIN 7  // Buzzer is connected to PWM pin GP7

// Define a melody for "Wheels on the Bus" using approximate frequencies:
// C = 262 Hz, F = 349 Hz, A = 440 Hz, ^C = 523 Hz, G = 392 Hz, E = 330 Hz
MelodyPlayer::Note myMelody[] = {
  // First verse: "The wheels on the bus"
  {262, 700},  // C (700 ms)
  {349, 700},  // F (700 ms)
  {349, 400},  // F (400 ms)
  {349, 400},  // F (400 ms)
  {349, 700},  // F (700 ms)
  
  // "Go round and round"
  {440, 500},  // A (500 ms)
  {523, 700},  // ^C (700 ms)
  {440, 500},  // A (500 ms)
  {349, 700},  // F (700 ms)
  
  // "Round and round"
  {392, 800},  // G (800 ms)
  {330, 600},  // E (600 ms)
  {262, 600},  // C (600 ms)
  
  // "Round and round!"
  {440, 700},  // A (700 ms)
  {392, 500},  // G (500 ms)
  {349, 700},  // F (700 ms)
  
  // Second verse: "The wheels on the bus"
  {262, 700},  // C (700 ms)
  {349, 700},  // F (700 ms)
  {349, 400},  // F (400 ms)
  {349, 400},  // F (400 ms)
  {349, 700},  // F (700 ms)
  
  // "Go round and round"
  {440, 500},  // A (500 ms)
  {523, 700},  // ^C (700 ms)
  {440, 500},  // A (500 ms)
  {349, 700},  // F (700 ms)
  
  // "All through the town!"
  {392, 600},  // G (600 ms)
  {262, 800},  // C (800 ms)
  {262, 800},  // C (800 ms)
  {349, 700}   // F (700 ms)
};
const int melodyLength = sizeof(myMelody) / sizeof(myMelody[0]);

// Create a MelodyPlayer instance.
MelodyPlayer player(BUZZER_PIN, myMelody, melodyLength, 50);

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("Press ButtonA to toggle the melody.");
}

void loop() {
  // Use a static variable to detect a rising edge.
  static bool lastButtonState = false;
  bool currentButtonState = buttonA.isPressed();

  // On rising edge, toggle the melody.
  if (currentButtonState && !lastButtonState) {
    if (player.isPlaying()) {
      player.stop();
      Serial.println("Melody stopped.");
    } else {
      player.start();
      Serial.println("Melody started.");
    }
    delay(200); // Debounce delay.
  }
  lastButtonState = currentButtonState;
  
  // Update the melody playback.
  player.update();
  
  yield(); // Allow background tasks to run.
}