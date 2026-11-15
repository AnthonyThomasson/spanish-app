import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createWait } from './wait';

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('createWait', () => {
  it('resolves true after the duration', async () => {
    const wait = createWait({ isCancelled: () => false, isPaused: () => false });
    const result = wait(1000);
    await vi.advanceTimersByTimeAsync(1000);
    expect(await result).toBe(true);
  });

  it('resolves false when cancelled', async () => {
    let cancelled = false;
    const wait = createWait({ isCancelled: () => cancelled, isPaused: () => false });
    const result = wait(1000);
    cancelled = true;
    await vi.advanceTimersByTimeAsync(200);
    expect(await result).toBe(false);
  });

  it('does not count paused time', async () => {
    let paused = false;
    const wait = createWait({ isCancelled: () => false, isPaused: () => paused });
    let done = false;
    void wait(1000).then(() => { done = true; });
    await vi.advanceTimersByTimeAsync(500);
    paused = true;
    await vi.advanceTimersByTimeAsync(5000);
    expect(done).toBe(false);
    paused = false;
    await vi.advanceTimersByTimeAsync(600);
    expect(done).toBe(true);
  });

  it('is wall-clock based, so throttled timers in a hidden page still finish on time', async () => {
    const wait = createWait({ isCancelled: () => false, isPaused: () => false });
    let done = false;
    void wait(3000).then(() => { done = true; });
    // The page was throttled: one late wake-up covering several seconds.
    vi.setSystemTime(Date.now() + 4000);
    await vi.advanceTimersByTimeAsync(100);
    expect(done).toBe(true);
  });
});
