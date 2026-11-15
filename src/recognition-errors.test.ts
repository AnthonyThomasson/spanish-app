import { describe, expect, it } from 'vitest';
import { RecognitionFailureTracker, classifyNativeRecognitionError, recognitionFailureMessage } from './recognition-errors';

describe('classifyNativeRecognitionError', () => {
  it('maps permission problems to not-allowed', () => {
    expect(classifyNativeRecognitionError('Insufficient permissions')).toBe('not-allowed');
    expect(classifyNativeRecognitionError('Missing permission')).toBe('not-allowed');
    expect(classifyNativeRecognitionError('Permission denied')).toBe('not-allowed');
  });

  it('treats silence as no-speech', () => {
    expect(classifyNativeRecognitionError('No match')).toBe('no-speech');
    expect(classifyNativeRecognitionError('No speech input')).toBe('no-speech');
    expect(classifyNativeRecognitionError("Didn't understand, please try again.")).toBe('no-speech');
  });

  it('treats everything else as a start failure', () => {
    expect(classifyNativeRecognitionError('Audio recording error')).toBe('audio-capture');
    expect(classifyNativeRecognitionError('RecognitionService busy')).toBe('audio-capture');
    expect(classifyNativeRecognitionError('Client side error')).toBe('audio-capture');
  });
});

describe('RecognitionFailureTracker', () => {
  it('trips after the threshold of consecutive failures', () => {
    const tracker = new RecognitionFailureTracker(3);
    expect(tracker.record()).toBe(false);
    expect(tracker.record()).toBe(false);
    expect(tracker.record()).toBe(true);
  });

  it('resets on success', () => {
    const tracker = new RecognitionFailureTracker(2);
    tracker.record();
    tracker.reset();
    expect(tracker.record()).toBe(false);
  });
});

describe('recognitionFailureMessage', () => {
  it('explains the background limitation when hidden', () => {
    expect(recognitionFailureMessage('not-allowed', true)).toMatch(/background/i);
    expect(recognitionFailureMessage('audio-capture', true)).toMatch(/Resume/);
  });

  it('gives permission advice in the foreground', () => {
    expect(recognitionFailureMessage('not-allowed', false)).toMatch(/Microphone access is blocked/);
    expect(recognitionFailureMessage('service-not-allowed', false)).toMatch(/Microphone access is blocked/);
  });

  it('gives a retry message for repeated start failures in the foreground', () => {
    expect(recognitionFailureMessage('audio-capture', false)).toMatch(/Resume/);
  });
});
