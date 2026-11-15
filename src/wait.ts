export interface WaitOptions {
  isCancelled(): boolean;
  isPaused(): boolean;
}

/**
 * Builds a cancellable, pausable delay. Elapsed time is measured with Date.now() rather than by
 * counting ticks, so a hidden page whose timers are throttled still finishes on time.
 */
export function createWait({ isCancelled, isPaused }: WaitOptions): (milliseconds: number) => Promise<boolean> {
  return (milliseconds) => {
    let remaining = milliseconds;
    let previous = Date.now();
    return new Promise((resolve) => {
      const tick = () => {
        if (isCancelled()) {
          resolve(false);
          return;
        }
        const now = Date.now();
        if (!isPaused()) remaining -= now - previous;
        previous = now;
        if (remaining <= 0) resolve(true);
        else setTimeout(tick, Math.min(100, remaining));
      };
      tick();
    });
  };
}
