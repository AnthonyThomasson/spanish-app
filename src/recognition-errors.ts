export type NativeRecognitionError = 'not-allowed' | 'no-speech' | 'audio-capture' | 'network' | 'busy';

/**
 * Maps the native plugin's rejection message onto the Web Speech error names the session understands.
 * Network, client-side and busy errors say nothing about the microphone, so they get their own names
 * and are retried without counting toward the pause.
 */
export function classifyNativeRecognitionError(message: string): NativeRecognitionError {
  const text = message.toLowerCase();
  if (text.includes('permission') || text.includes('denied')) return 'not-allowed';
  if (text.includes('no match') || text.includes('no speech') || text.includes('understand')) return 'no-speech';
  if (text.includes('busy')) return 'busy';
  if (text.includes('network') || text.includes('client side') || text.includes('server')) return 'network';
  return 'audio-capture';
}

/** Errors that say nothing about whether the microphone works. */
const TRANSIENT_ERRORS = ['network', 'busy'];

/** How long to wait before listening again; a busy recognizer needs longer to free up. */
export function recognitionRetryDelay(error: string): number {
  return error === 'busy' ? 1000 : 250;
}

/** Counts consecutive recognition failures so a broken microphone doesn't retry forever. */
export class RecognitionFailureTracker {
  private failures = 0;

  constructor(private readonly threshold = 3) {}

  /** Records a failure; returns true once the threshold is reached. */
  record(): boolean {
    this.failures += 1;
    return this.failures >= this.threshold;
  }

  reset(): void {
    this.failures = 0;
  }
}

export type RecognitionVerdict = 'pause' | 'silence' | 'retry';

/**
 * Decides what a recognition error means for a Speak answers session: keep waiting through silence,
 * retry after a transient failure, or give up and pause. Only native Android pauses on repeated trouble.
 */
export class RecognitionMonitor {
  private readonly failures = new RecognitionFailureTracker(3);
  private readonly silences = new RecognitionFailureTracker(5);

  handle(error: string, context: { native: boolean; hidden: boolean }): RecognitionVerdict {
    if (error === 'not-allowed' || error === 'service-not-allowed') return 'pause';
    if (error === 'no-speech') {
      this.failures.reset();
      // In the background Android may block the microphone in a way that only looks like silence.
      if (context.native && context.hidden) return this.silences.record() ? 'pause' : 'silence';
      this.silences.reset();
      return 'silence';
    }
    if (TRANSIENT_ERRORS.includes(error)) return 'retry';
    return context.native && this.failures.record() ? 'pause' : 'retry';
  }

  reset(): void {
    this.failures.reset();
    this.silences.reset();
  }
}

const isBlocked = (error: string) => error === 'not-allowed' || error === 'service-not-allowed';

/** `native` is true on Android, where the permission lives in the app/phone settings rather than a browser. */
export function recognitionFailureMessage(error: string, hidden: boolean, native = false): string {
  const blocked = isBlocked(error);
  if (hidden) {
    return blocked
      ? 'Microphone access was blocked while the app was in the background. Open the app and press Resume.'
      : 'The microphone stopped working in the background. Open the app and press Resume to try again.';
  }
  if (blocked) {
    return native
      ? 'Microphone access is blocked. Allow it in your phone’s app settings, then press Resume.'
      : 'Microphone access is blocked. Allow it in your browser settings, then press Resume.';
  }
  return 'The microphone isn’t responding. Press Resume to try again.';
}

/** Short version of the failure for the notification, which can't show more than a line or two. */
export function recognitionFailureNotice(error: string, background: boolean): string {
  if (background) {
    return isBlocked(error)
      ? 'Microphone blocked in the background — open the app and press Resume'
      : 'Microphone stopped in the background — open the app and press Resume';
  }
  return isBlocked(error)
    ? 'Microphone blocked — allow it in the app settings, then press Resume'
    : 'The microphone isn’t responding — press Resume to retry';
}
