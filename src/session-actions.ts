export type BackgroundAction = 'pause' | 'resume' | 'skip' | 'stop';

export interface SessionControls {
  isActive(): boolean;
  isPaused(): boolean;
  pause(): void;
  resume(): void;
  skip(): void;
  stop(): void;
}

/** Applies a notification button press. Pause and resume are idempotent. */
export function dispatchBackgroundAction(action: BackgroundAction, controls: SessionControls): void {
  if (!controls.isActive()) return;
  switch (action) {
    case 'pause':
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
