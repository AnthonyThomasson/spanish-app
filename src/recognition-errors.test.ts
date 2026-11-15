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

  it('treats network and busy errors as transient, not audio failures', () => {
    expect(classifyNativeRecognitionError('Network error')).toBe('network');
    expect(classifyNativeRecognitionError('Network timeout')).toBe('network');
    expect(classifyNativeRecognitionError('error from server')).toBe('network');
    expect(classifyNativeRecognitionError('RecognitionService busy')).toBe('busy');
  });

  it('counts a client side error like an audio failure', () => {
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

describe('recognitionFailureMessage for unreachable recognition', () => {
  it('asks the user to check their connection', () => {
    expect(recognitionFailureMessage('network', false, true)).toBe('Speech recognition isn’t reachable — check your connection, then press Resume.');
    expect(recognitionFailureMessage('busy', true, true)).toMatch(/check your connection/);
  });
});

describe('recognitionFailureNotice', () => {
  it('stays short enough for one notification line', () => {
    const cases: Array<[string, boolean]> = [
      ['not-allowed', true], ['not-allowed', false], ['no-speech', true], ['audio-capture', false], ['network', false],
    ];
    for (const [error, background] of cases) expect(recognitionFailureNotice(error, background).length).toBeLessThanOrEqual(45);
  });

  it('explains each failure', () => {
    expect(recognitionFailureNotice('not-allowed', true)).toBe('Mic blocked — open app, press Resume');
    expect(recognitionFailureNotice('no-speech', true)).toBe('Mic stopped — open app, press Resume');
    expect(recognitionFailureNotice('not-allowed', false)).toBe('Mic blocked — check settings, press Resume');
    expect(recognitionFailureNotice('audio-capture', false)).toBe('Mic not responding — press Resume');
    expect(recognitionFailureNotice('network', false)).toBe('Speech offline — check connection, Resume');
  });
});

describe('recognitionRetryDelay', () => {
  it('retries quickly after silence or a microphone error', () => {
    expect(recognitionRetryDelay('no-speech')).toBe(250);
    expect(recognitionRetryDelay('audio-capture')).toBe(250);
  });

  it('backs off exponentially for transient errors, up to a cap', () => {
    expect([1, 2, 3, 4, 5, 6].map((n) => recognitionRetryDelay('network', n))).toEqual([250, 500, 1000, 2000, 4000, 4000]);
    expect(recognitionRetryDelay('network', 50)).toBe(4000);
  });

  it('starts a busy recognizer at a longer delay', () => {
    expect(recognitionRetryDelay('busy', 1)).toBe(1000);
    expect(recognitionRetryDelay('busy', 2)).toBe(2000);
    expect(recognitionRetryDelay('busy', 5)).toBe(4000);
  });
});

describe('RecognitionMonitor transient errors', () => {
  const foreground = { native: true, hidden: false };

  it('retries network and busy errors, then pauses after about ten in a row', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 9; i++) expect(monitor.handle(i % 2 ? 'busy' : 'network', foreground)).toBe('retry');
    expect(monitor.handle('network', foreground)).toBe('pause');
  });

  it('never pauses a browser for transient errors', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 30; i++) expect(monitor.handle('network', { native: false, hidden: false })).toBe('retry');
  });

  it('is independent of the audio-failure count', () => {
    const monitor = new RecognitionMonitor();
    monitor.handle('audio-capture', foreground);
    monitor.handle('network', foreground);
    monitor.handle('busy', foreground);
    monitor.handle('audio-capture', foreground);
    expect(monitor.handle('audio-capture', foreground)).toBe('pause');
  });

  it('restarts the transient count after silence proves the recognizer works, or on reset', () => {
    const monitor = new RecognitionMonitor();
    for (let i = 0; i < 9; i++) monitor.handle('network', foreground);
    monitor.handle('no-speech', foreground);
    for (let i = 0; i < 9; i++) expect(monitor.handle('network', foreground)).toBe('retry');
    monitor.reset();
    for (let i = 0; i < 9; i++) expect(monitor.handle('network', foreground)).toBe('retry');
  });

  it('reports the retry delay for the current run of transient errors', () => {
    const monitor = new RecognitionMonitor();
    monitor.handle('network', foreground);
    expect(monitor.retryDelay('network')).toBe(250);
    monitor.handle('network', foreground);
    monitor.handle('network', foreground);
    expect(monitor.retryDelay('network')).toBe(1000);
    monitor.handle('no-speech', foreground);
    expect(monitor.retryDelay('no-speech')).toBe(250);
  });
});
