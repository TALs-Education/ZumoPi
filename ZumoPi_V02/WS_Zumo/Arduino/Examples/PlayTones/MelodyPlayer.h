#ifndef MELODYPLAYER_H
#define MELODYPLAYER_H

#include <Arduino.h>

class MelodyPlayer {
public:
  // A Note consists of a frequency (Hz) and a duration (ms).
  struct Note {
    uint16_t frequency;
    unsigned long duration;
  };

  // Constructor:
  // buzzerPin: the PWM pin connected to the buzzer.
  // melody: pointer to an array of Note.
  // melodyLength: number of notes in the melody.
  // gapBetweenNotes: pause (ms) between notes (default 50 ms).
  MelodyPlayer(int buzzerPin, const Note* melody, int melodyLength, unsigned long gapBetweenNotes = 50);

  // Start playing the melody from the beginning.
  void start();

  // update() should be called repeatedly (e.g., in loop()).
  // Returns true if the melody is still playing.
  bool update();

  // Stop the melody immediately.
  void stop();

  // Returns true if the melody is currently playing.
  bool isPlaying() const;

private:
  int _buzzerPin;
  const Note* _melody;
  int _melodyLength;
  unsigned long _gapBetweenNotes;
  int _currentNote;
  unsigned long _noteStartTime;
  bool _isPlaying;
};

#endif