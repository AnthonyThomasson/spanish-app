import { describe, expect, it, vi } from 'vitest';
import { createBackgroundSession, type BackgroundSessionPlugin } from './background-session';

function fakePlugin() {
  const listeners: Array<(event: { action: 'pause' | 'resume' | 'skip' | 'stop' }) => void> = [];
  const remove = vi.fn(async () => {});
  const plugin = {
    start: vi.fn(async () => {}),
    update: vi.fn(async () => {}),
    stop: vi.fn(async () => {}),
    addListener: vi.fn(async (_name: 'action', listener: (typeof listeners)[number]) => {
      listeners.push(listener);
      return { remove };
    }),
  } satisfies BackgroundSessionPlugin;
  return { plugin, listeners, remove };
}

const state = { title: 'Auto listen · 1 / 5', text: 'hola', paused: false, mode: 'auto' as const };

describe('createBackgroundSession', () => {
  it('is a complete no-op when disabled (browser / iOS)', async () => {
    const { plugin } = fakePlugin();
    const session = createBackgroundSession(plugin, false);
    session.sync(state);
    session.stop();
    const unsubscribe = await session.onAction(() => {});
    unsubscribe();
    expect(plugin.start).not.toHaveBeenCalled();
    expect(plugin.update).not.toHaveBeenCalled();
    expect(plugin.stop).not.toHaveBeenCalled();
    expect(plugin.addListener).not.toHaveBeenCalled();
  });

  it('starts on the first sync and updates afterwards, without the mode', async () => {
    const { plugin } = fakePlugin();
    const session = createBackgroundSession(plugin, true);
    session.sync(state);
    session.sync({ ...state, text: 'hola → hello', paused: true });
    await session.idle();
    expect(plugin.start).toHaveBeenCalledExactlyOnceWith(state);
    expect(plugin.update).toHaveBeenCalledExactlyOnceWith({ title: state.title, text: 'hola → hello', paused: true });
  });

  it('starts again after stop', async () => {
    const { plugin } = fakePlugin();
    const session = createBackgroundSession(plugin, true);
    session.sync(state);
    session.stop();
    session.sync(state);
    await session.idle();
    expect(plugin.start).toHaveBeenCalledTimes(2);
    expect(plugin.stop).toHaveBeenCalledOnce();
  });

  it('keeps calls in order even when start is slow', async () => {
    const { plugin } = fakePlugin();
    const order: string[] = [];
    plugin.start.mockImplementation(async () => { await new Promise((r) => setTimeout(r, 20)); order.push('start'); });
    plugin.update.mockImplementation(async () => { order.push('update'); });
    plugin.stop.mockImplementation(async () => { order.push('stop'); });
    const session = createBackgroundSession(plugin, true);
    session.sync(state);
    session.sync(state);
    session.stop();
    await session.idle();
    expect(order).toEqual(['start', 'update', 'stop']);
  });

  it('swallows plugin errors and keeps working', async () => {
    const { plugin } = fakePlugin();
    plugin.start.mockRejectedValueOnce(new Error('boom'));
    const session = createBackgroundSession(plugin, true);
    session.sync(state);
    session.sync(state);
    await session.idle();
    expect(plugin.update).toHaveBeenCalledOnce();
  });

  it('retries start on the next sync if starting failed', async () => {
    const { plugin } = fakePlugin();
    plugin.start.mockRejectedValueOnce(new Error('boom'));
    const session = createBackgroundSession(plugin, true);
    session.sync(state);
    await session.idle();
    session.sync(state);
    await session.idle();
    expect(plugin.start).toHaveBeenCalledTimes(2);
    expect(plugin.update).not.toHaveBeenCalled();
  });

  it('forwards notification actions and can unsubscribe', async () => {
    const { plugin, listeners, remove } = fakePlugin();
    const session = createBackgroundSession(plugin, true);
    const handler = vi.fn();
    const unsubscribe = await session.onAction(handler);
    listeners[0]({ action: 'skip' });
    expect(handler).toHaveBeenCalledWith('skip');
    unsubscribe();
    expect(remove).toHaveBeenCalledOnce();
  });
});
