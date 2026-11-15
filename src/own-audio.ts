/**
 * Tracks our own audio activity (text-to-speech and the speech recognizer). Both take Android audio
 * focus themselves, so the focus-loss events they cause must not be mistaken for another app (a phone
 * call) taking the audio. The system delivers those events asynchronously, so activity counts for a
 * short grace period after it ends.
 */
export interface OwnAudioGuard {
  /** Marks audio as playing until the returned function is called (calling it again does nothing). */
  begin(): () => void;
  /** Marks a moment of our own audio activity without holding it open (for example, the recognizer closing). */
  touch(): void;
  isActive(): boolean;
}

const DEFAULT_GRACE_MS = 2000;

export function createOwnAudioGuard(now: () => number = () => Date.now(), graceMs = DEFAULT_GRACE_MS): OwnAudioGuard {
  let playing = 0;
  let lastActivity = Number.NEGATIVE_INFINITY;
  return {
    begin() {
      playing += 1;
      lastActivity = now();
      let ended = false;
      return () => {
        if (ended) return;
        ended = true;
        playing -= 1;
        lastActivity = now();
      };
    },
    touch() {
      lastActivity = now();
    },
    isActive: () => playing > 0 || now() - lastActivity < graceMs,
  };
}

export const ownAudio = createOwnAudioGuard();
