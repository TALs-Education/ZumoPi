#include "MelodyPlayer.h"

MelodyPlayer::MelodyPlayer(int buzzerPin, const Note* melody, int melodyLength, unsigned long gapBetweenNotes)
  : _buzzerPin(buzzerPin),
    _melody(melody),
    _melodyLength(melodyLength),
    _gapBetweenNotes(gapBetweenNotes),
    _currentNote(0),
    _noteStartTime(0),
    _isPlaying(false)
{
  pinMode(_buzzerPin, OUTPUT);
}

void MelodyPlayer::start() {
  _isPlaying = true;
  _currentNote = 0;
  _noteStartTime = 0;
}

bool MelodyPlayer::update() {
  if (!_isPlaying)
    return false;
  
  unsigned long currentTime = millis();
  if (_currentNote < _melodyLength) {
    if (_noteStartTime == 0) {
      // Begin playing the current note.
      tone(_buzzerPin, _melody[_currentNote].frequency);
      _noteStartTime = currentTime;
    }
    // Check if the note's duration has elapsed.
    if (currentTime - _noteStartTime >= _melody[_currentNote].duration) {
      noTone(_buzzerPin);
      // Wait for the gap between notes.
      if (currentTime - _noteStartTime >= _melody[_currentNote].duration + _gapBetweenNotes) {
        _currentNote++;
        _noteStartTime = 0;  // Prepare for the next note.
      }
    }
    return true;  // Still playing.
  } else {
    _isPlaying = false;
    return false; // Melody finished.
  }
}

void MelodyPlayer::stop() {
  noTone(_buzzerPin);
  _isPlaying = false;
  _currentNote = _melodyLength; // Mark as finished.
}

bool MelodyPlayer::isPlaying() const {
  return _isPlaying;
}