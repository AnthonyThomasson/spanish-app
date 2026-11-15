export type NativeRecognitionError = 'not-allowed' | 'no-speech' | 'audio-capture' | 'network' | 'busy';

/**
 * Maps the native plugin's rejection message onto the Web Speech error names the session understands.
 * Network and busy errors say nothing about the microphone, so they get their own names and are
 * retried without counting toward the audio-failure pause (they have their own, larger cap).
 */
export function classifyNativeRecognitionError(message: string): NativeRecognitionError {
  const text = message.toLowerCase();
  if (text.includes('permission') || text.includes('denied')) return 'not-allowed';
  if (text.includes('no match') || text.includes('no speech') || text.includes('understand')) return 'no-speech';
  if (text.includes('busy')) return 'busy';
  if (text.includes('network') || text.includes('server')) return 'network';
  return 'audio-capture';
}

/** Errors that say nothing about whether the microphone works. */
const TRANSIENT_ERRORS = ['network', 'busy'];
export const isTransientError = (error: string): boolean => TRANSIENT_ERRORS.includes(error);

const RETRY_DELAY_MS = 250;
const BUSY_RETRY_DELAY_MS = 1000;
const MAX_RETRY_DELAY_MS = 4000;

/**
 * How long to wait before listening again. Transient errors back off exponentially with the number of
 * consecutive ones (a busy recognizer starts higher); anything else retries quickly.
 */
export function recognitionRetryDelay(error: string, consecutiveTransient = 0): number {
  if (!isTransientError(error)) return RETRY_DELAY_MS;
  const base = error === 'busy' ? BUSY_RETRY_DELAY_MS : RETRY_DELAY_MS;
  return Math.min(MAX_RETRY_DELAY_MS, base * 2 ** Math.max(0, consecutiveTransient - 1));
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
  private readonly transients = new RecognitionFailureTracker(10);
  private transientCount = 0;

  handle(error: string, context: { native: boolean; hidden: boolean }): RecognitionVerdict {
    if (error === 'not-allowed' || error === 'service-not-allowed') return 'pause';
    if (error === 'no-speech') {
      this.failures.reset();
      this.transients.reset();
      this.transientCount = 0;
      // In the background Android may block the microphone in a way that only looks like silence.
      if (context.native && context.hidden) return this.silences.record() ? 'pause' : 'silence';
      this.silences.reset();
      return 'silence';
    }
    if (isTransientError(error)) {
      this.transientCount += 1;
      return context.native && this.transients.record() ? 'pause' : 'retry';
    }
    return context.native && this.failures.record() ? 'pause' : 'retry';
  }

  /** Delay before the next listen attempt, given the run of errors seen so far. */
  retryDelay(error: string): number {
    return recognitionRetryDelay(error, this.transientCount);
  }

  reset(): void {
    this.failures.reset();
    this.silences.reset();
    this.transients.reset();
    this.transientCount = 0;
  }
}

const isBlocked = (error: string) => error === 'not-allowed' || error === 'service-not-allowed';

/** `native` is true on Android, where the permission lives in the app/phone settings rather than a browser. */
export function recognitionFailureMessage(error: string, hidden: boolean, native = false): string {
  const blocked = isBlocked(error);
  if (isTransientError(error)) return 'Speech recognition isn’t reachable — check your connection, then press Resume.';
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

/** Short version of the failure for the notification, which shows one line. The page status has the full text. */
export function recognitionFailureNotice(error: string, background: boolean): string {
  if (isTransientError(error)) return 'Speech offline — check connection, Resume';
  if (background) {
    return isBlocked(error) ? 'Mic blocked — open app, press Resume' : 'Mic stopped — open app, press Resume';
  }
  return isBlocked(error) ? 'Mic blocked — check settings, press Resume' : 'Mic not responding — press Resume';
}
