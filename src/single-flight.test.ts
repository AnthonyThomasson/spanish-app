import { describe, expect, it, vi } from 'vitest';
import { singleFlight } from './single-flight';

describe('singleFlight', () => {
  it('ignores calls made while a previous one is still running', async () => {
    let release!: () => void;
    const task = vi.fn(() => new Promise<void>((resolve) => { release = resolve; }));
    const guarded = singleFlight(task);
    const first = guarded();
    await guarded();
    await guarded();
    expect(task).toHaveBeenCalledOnce();
    release();
    await first;
    void guarded();
    expect(task).toHaveBeenCalledTimes(2);
  });

  it('reports busy state changes, even if the task throws', async () => {
    const onBusy = vi.fn();
    const guarded = singleFlight(async () => { throw new Error('boom'); }, onBusy);
    await expect(guarded()).rejects.toThrow('boom');
    expect(onBusy.mock.calls).toEqual([[true], [false]]);
    await expect(guarded()).rejects.toThrow('boom');
  });
});
