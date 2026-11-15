import { describe, expect, it } from 'vitest';
import {
  RecognitionFailureTracker,
  RecognitionMonitor,
  classifyNativeRecognitionError,
  recognitionFailureMessage,
  recognitionFailureNotice,
  recognitionRetryDelay,
} from './recognition-errors';

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

  it('treats genuine audio failures as audio-capture', () => {
    expect(classifyNativeRecognitionError('Audio recording error')).toBe('audio-capture');
    expect(classifyNativeRecognitionError('Something unexpected')).toBe('audio-capture');
  });

  it('treats network, client and busy errors as transient, not audio failures', () => {
    expect(classifyNativeRecognitionError('Network error')).toBe('network');
    expect(classifyNativeRecognitionError('Network timeout')).toBe('network');
    expect(classifyNativeRecognitionError('error from server')).toBe('network');
    expect(classifyNativeRecognitionError('Client side error')).toBe('network');
    expect(classifyNativeRecognitionError('RecognitionService busy')).toBe('busy');
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
  it('points Android users at app settings, not browser settings', () => {
    const message = recognitionFailureMessage('not-allowed', false, true);
    expect(message).not.toMatch(/browser/i);
    expect(message).toMatch(/app settings|phone settings/i);
    expect(recognitionFailureMessage('not-allowed', false)).toMatch(/browser settings/);
  });

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

describe('RecognitionMonitor', () => {
  const foreground = { native: true, hidden: false };
  const background = { native: true, hidden: true };

  it('pauses immediately when the microphone is blocked', () => {
    const monitor = new RecognitionMonitor();
    expect(monitor.handle('not-allowed', foreground)).toBe('pause');
    expect(monitor.handle('service-not-allowed', foreground)).toBe('pause');
  });

  it('retries silence in the foreground forever', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 20; i++) expect(monitor.handle('no-speech', foreground)).toBe('silence');
  });

  it('pauses after repeated silence while hidden on native', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 4; i++) expect(monitor.handle('no-speech', background)).toBe('silence');
    expect(monitor.handle('no-speech', background)).toBe('pause');
  });

  it('does not cap silence in a browser', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 10; i++) expect(monitor.handle('no-speech', { native: false, hidden: true })).toBe('silence');
  });

  it('restarts the silence count after a result or when the page is visible again', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 4; i++) monitor.handle('no-speech', background);
    monitor.reset();
    expect(monitor.handle('no-speech', background)).toBe('silence');
    for (let i = 0; i < 3; i++) monitor.handle('no-speech', background);
    monitor.handle('no-speech', foreground);
    for (let i = 0; i < 4; i++) expect(monitor.handle('no-speech', background)).toBe('silence');
  });

  it('pauses after three consecutive start failures on native only', () => {
    const monitor = new RecognitionMonitor();
    expect(monitor.handle('audio-capture', foreground)).toBe('retry');
    expect(monitor.handle('audio-capture', foreground)).toBe('retry');
    expect(monitor.handle('audio-capture', foreground)).toBe('pause');
    const browser = new RecognitionMonitor();
    for (let i = 0; i < 10; i++) expect(browser.handle('network', { native: false, hidden: false })).toBe('retry');
  });

  it('counts a silent attempt as proof the microphone works', () => {
    const monitor = new RecognitionMonitor();
    monitor.handle('audio-capture', foreground);
    monitor.handle('audio-capture', foreground);
    monitor.handle('no-speech', foreground);
    expect(monitor.handle('audio-capture', foreground)).toBe('retry');
  });
});

describe('recognitionFailureNotice', () => {
  it('explains a background block and a foreground failure for the notification', () => {
    expect(recognitionFailureNotice('not-allowed', true)).toBe('Microphone blocked in the background — open the app and press Resume');
    expect(recognitionFailureNotice('no-speech', true)).toMatch(/background/);
    expect(recognitionFailureNotice('audio-capture', false)).toBe('The microphone isn’t responding — press Resume to retry');
    expect(recognitionFailureNotice('not-allowed', false)).toMatch(/Resume/);
  });
});

describe('recognitionRetryDelay', () => {
  it('retries quickly, but backs off when the recognizer is busy', () => {
    expect(recognitionRetryDelay('no-speech')).toBe(250);
    expect(recognitionRetryDelay('network')).toBe(250);
    expect(recognitionRetryDelay('busy')).toBeGreaterThan(250);
  });
});

describe('RecognitionMonitor transient errors', () => {
  const foreground = { native: true, hidden: false };

  it('never pauses for network, client or busy errors', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 20; i++) expect(monitor.handle('network', foreground)).toBe('retry');
    for (let i = 0; i < 20; i++) expect(monitor.handle('busy', foreground)).toBe('retry');
  });

  it('does not count them toward the audio-failure pause or clear it', () => {
    const monitor = new RecognitionMonitor();
    monitor.handle('audio-capture', foreground);
    monitor.handle('network', foreground);
    monitor.handle('busy', foreground);
    monitor.handle('audio-capture', foreground);
    expect(monitor.handle('audio-capture', foreground)).toBe('pause');
  });
});
