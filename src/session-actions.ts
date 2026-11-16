export type BackgroundAction = 'pause' | 'resume' | 'skip' | 'stop';
export type BackgroundActionSource = 'notification' | 'audio-focus';

/** What the native side knows about an audio-focus loss. */
export interface FocusLossInfo {
  /** The raw AudioManager focus change code, for the debug log. */
  focusChange?: number;
  /** Transient losses are what our own speech and recognizer cause; a permanent loss never is. */
  transient?: boolean;
  /** The phone is ringing or in a call (including VoIP). */
  call?: boolean;
}

export interface SessionControls {
  isActive(): boolean;
  isPaused(): boolean;
  /** True while our own speech recognizer is open. */
  isListening(): boolean;
  /** True while our own speech or recognizer audio is active (or just ended): it takes audio focus itself. Speak answers only. */
  isOwnAudio(): boolean;
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
  focus?: FocusLossInfo,
): void {
  if (!controls.isActive()) return;
  switch (action) {
    case 'pause':
      if (source === 'audio-focus' && isOurOwnAudioFocusLoss(controls, focus)) {
        logPause('ignored', source, controls, focus);
        break;
      }
      if (!controls.isPaused()) {
        logPause('pausing', source, controls, focus);
        controls.pause();
      }
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

/**
 * Our own speech synthesis and the system recognizer take transient audio focus themselves; that must
 * not pause Speak answers. A permanent loss or a call always does. An older native build sends no detail
 * and is treated as a plain transient loss.
 */
function isOurOwnAudioFocusLoss(controls: SessionControls, focus?: FocusLossInfo): boolean {
  if (focus?.call || focus?.transient === false) return false;
  return controls.isListening() || controls.isOwnAudio();
}

/** Debug log for chrome://inspect: why a pause was honoured or ignored. */
export function logPause(
  outcome: string,
  source: string,
  controls: Pick<SessionControls, 'isListening' | 'isOwnAudio'>,
  focus?: FocusLossInfo,
): void {
  console.info(
    `[session] pause ${outcome} source=${source} focusChange=${focus?.focusChange ?? 'n/a'} transient=${focus?.transient ?? 'n/a'} call=${focus?.call ?? 'n/a'} listening=${controls.isListening()} ownAudio=${controls.isOwnAudio()}`,
  );
}
