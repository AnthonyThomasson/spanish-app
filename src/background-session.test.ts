import { describe, expect, it, vi } from 'vitest';
import { createBackgroundSession, type BackgroundSessionPlugin } from './background-session';

function fakePlugin() {
  const listeners: Array<(event: { action: 'pause' | 'resume' | 'skip' | 'stop'; source?: 'notification' | 'audio-focus' }) => void> = [];
  const appStateListeners: Array<(event: { background: boolean }) => void> = [];
  const remove = vi.fn(async () => {});
  const plugin = {
    start: vi.fn(async () => {}),
    update: vi.fn(async () => {}),
    stop: vi.fn(async () => {}),
    getState: vi.fn(async () => ({ background: false })),
    addListener: vi.fn(async (name: string, listener: (event: never) => void) => {
      if (name === 'action') listeners.push(listener as (typeof listeners)[number]);
      else appStateListeners.push(listener as (event: { background: boolean }) => void);
      return { remove };
    }),
  } satisfies BackgroundSessionPlugin;
  return { plugin, listeners, appStateListeners, remove };
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
    expect(plugin.getState).not.toHaveBeenCalled();
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

  it('does not let an old failed start clobber a newer start', async () => {
    const { plugin } = fakePlugin();
    plugin.start.mockImplementationOnce(async () => { await new Promise((r) => setTimeout(r, 10)); throw new Error('late'); });
    const session = createBackgroundSession(plugin, true);
    session.sync(state); // start A (will fail late)
    session.stop();
    session.sync(state); // start B
    await session.idle();
    session.sync(state); // should be an update: B is running
    await session.idle();
    expect(plugin.start).toHaveBeenCalledTimes(2);
    expect(plugin.update).toHaveBeenCalledOnce();
  });

  it('forwards notification actions and can unsubscribe', async () => {
    const { plugin, listeners, remove } = fakePlugin();
    const session = createBackgroundSession(plugin, true);
    const handler = vi.fn();
    const unsubscribe = await session.onAction(handler);
    listeners[0]({ action: 'skip' });
    listeners[0]({ action: 'pause', source: 'audio-focus' });
    expect(handler).toHaveBeenNthCalledWith(1, 'skip', undefined);
    expect(handler).toHaveBeenNthCalledWith(2, 'pause', 'audio-focus');
    unsubscribe();
    expect(remove).toHaveBeenCalledOnce();
  });

  describe('isBackground', () => {
    it('follows document.hidden when disabled (browser)', () => {
      const { plugin } = fakePlugin();
      let hidden = false;
      const session = createBackgroundSession(plugin, false, () => hidden);
      expect(session.isBackground()).toBe(false);
      hidden = true;
      expect(session.isBackground()).toBe(true);
    });

    it('follows the native appState event and ignores document.hidden on native', async () => {
      const { plugin, appStateListeners } = fakePlugin();
      const session = createBackgroundSession(plugin, true, () => false);
      await session.watchAppState();
      expect(session.isBackground()).toBe(false);
      appStateListeners[0]({ background: true });
      expect(session.isBackground()).toBe(true);
      appStateListeners[0]({ background: false });
      expect(session.isBackground()).toBe(false);
    });

    it('does not treat a hidden document as background on native', async () => {
      const { plugin } = fakePlugin();
      const session = createBackgroundSession(plugin, true, () => true);
      await session.watchAppState();
      expect(session.isBackground()).toBe(false);
    });

    it('reads the initial native state with getState', async () => {
      const { plugin } = fakePlugin();
      plugin.getState.mockResolvedValueOnce({ background: true });
      const session = createBackgroundSession(plugin, true);
      await session.watchAppState();
      expect(session.isBackground()).toBe(true);
    });

    it('keeps working when an older native build has no getState or appState', async () => {
      const { plugin } = fakePlugin();
      plugin.getState.mockRejectedValueOnce(new Error('not implemented'));
      plugin.addListener.mockRejectedValueOnce(new Error('nope'));
      const session = createBackgroundSession(plugin, true);
      await expect(session.watchAppState()).resolves.toBeUndefined();
      expect(session.isBackground()).toBe(false);
    });
  });
});
