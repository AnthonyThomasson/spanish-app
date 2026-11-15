/** Maps the native plugin's rejection message onto the Web Speech error names the session understands. */
export function classifyNativeRecognitionError(message: string): 'not-allowed' | 'no-speech' | 'audio-capture' {
  const text = message.toLowerCase();
  if (text.includes('permission') || text.includes('denied')) return 'not-allowed';
  if (text.includes('no match') || text.includes('no speech') || text.includes('understand')) return 'no-speech';
  return 'audio-capture';
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
    return context.native && this.failures.record() ? 'pause' : 'retry';
  }

  reset(): void {
    this.failures.reset();
    this.silences.reset();
  }
}

export function recognitionFailureMessage(error: string, hidden: boolean): string {
  const blocked = error === 'not-allowed' || error === 'service-not-allowed';
  if (hidden) {
    return blocked
      ? 'Microphone access was blocked while the app was in the background. Open the app and press Resume.'
      : 'The microphone stopped working in the background. Open the app and press Resume to try again.';
  }
  return blocked
    ? 'Microphone access is blocked. Allow it in your browser settings, then press Resume.'
    : 'The microphone isn’t responding. Press Resume to try again.';
}
