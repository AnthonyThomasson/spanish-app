import { registerPlugin } from '@capacitor/core';
import type { NotificationState } from './notification';
import type { BackgroundAction } from './session-actions';
import { usingNativeSpeech } from './speech';

/** Native contract implemented by the Android BackgroundSession plugin. */
export interface BackgroundSessionPlugin {
  start(options: { title: string; text: string; paused: boolean; mode: 'auto' | 'answer' }): Promise<void>;
  update(options: { title: string; text: string; paused: boolean }): Promise<void>;
  stop(): Promise<void>;
  addListener(
    eventName: 'action',
    listener: (event: { action: BackgroundAction }) => void,
  ): Promise<{ remove(): Promise<void> }>;
}

export interface BackgroundSession {
  /** Starts the foreground service on the first call, then keeps the notification up to date. */
  sync(state: NotificationState): void;
  stop(): void;
  onAction(handler: (action: BackgroundAction) => void): Promise<() => void>;
  /** Resolves once every queued native call has finished. */
  idle(): Promise<void>;
}

export function createBackgroundSession(plugin: BackgroundSessionPlugin, enabled: boolean): BackgroundSession {
  let running = false;
  let queue: Promise<void> = Promise.resolve();

  // Native calls are chained so a slow start (it may ask for notification permission) can't be overtaken.
  const enqueue = (call: () => Promise<void>) => {
    queue = queue.then(call).catch(() => {});
  };

  return {
    sync(state) {
      if (!enabled) return;
      if (running) {
        const { title, text, paused } = state;
        enqueue(() => plugin.update({ title, text, paused }));
      } else {
        running = true;
        enqueue(() => plugin.start(state));
      }
    },
    stop() {
      if (!enabled) return;
      running = false;
      enqueue(() => plugin.stop());
    },
    async onAction(handler) {
      if (!enabled) return () => {};
      try {
        const handle = await plugin.addListener('action', (event) => handler(event.action));
        return () => { void handle.remove().catch(() => {}); };
      } catch {
        return () => {};
      }
    },
    idle: () => queue,
  };
}

export const backgroundSession = createBackgroundSession(
  registerPlugin<BackgroundSessionPlugin>('BackgroundSession'),
  usingNativeSpeech(),
);
