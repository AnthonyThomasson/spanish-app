/** Wraps an async function so overlapping calls are ignored until the running one settles. */
export function singleFlight(task: () => Promise<void>, onBusy?: (busy: boolean) => void): () => Promise<void> {
  let running = false;
  return async () => {
    if (running) return;
    running = true;
    onBusy?.(true);
    try {
      await task();
    } finally {
      running = false;
      onBusy?.(false);
    }
  };
}
