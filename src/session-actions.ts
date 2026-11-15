export type BackgroundAction = 'pause' | 'resume' | 'skip' | 'stop';
export type BackgroundActionSource = 'notification' | 'audio-focus';

export interface SessionControls {
  isActive(): boolean;
  isPaused(): boolean;
  /** True while our own speech recognizer is open. */
  isListening(): boolean;
  pause(): void;
  resume(): void;
  skip(): void;
  stop(): void;
}

/** Applies a notification button press. Pause and resume are idempotent. */
export function dispatchBackgroundAction(
  action: BackgroundAction,
  controls: SessionControls,
  source: BackgroundActionSource = 'notification',
): void {
  if (!controls.isActive()) return;
  switch (action) {
    case 'pause':
      // The system recognizer takes transient audio focus itself; that must not pause Speak answers.
      if (source === 'audio-focus' && controls.isListening()) break;
      if (!controls.isPaused()) controls.pause();
      break;
    case 'resume':
      if (controls.isPaused()) controls.resume();
      break;
    case 'skip':
      controls.skip();
      break;
    case 'stop':
      controls.stop();
      break;
  }
}
