import { registerPlugin } from '@capacitor/core';
import type { NotificationState } from './notification';
import type { BackgroundAction, BackgroundActionSource } from './session-actions';
import { usingNativeSpeech } from './speech';

/** Native contract implemented by the Android BackgroundSession plugin. */
export interface BackgroundSessionPlugin {
  start(options: { title: string; text: string; paused: boolean; mode: 'auto' | 'answer' }): Promise<void>;
  update(options: { title: string; text: string; paused: boolean }): Promise<void>;
  stop(): Promise<void>;
  /** Optional: absent from older native builds. */
  getState?(): Promise<{ background: boolean }>;
  addListener(
    eventName: 'action',
    listener: (event: { action: BackgroundAction; source?: BackgroundActionSource }) => void,
  ): Promise<{ remove(): Promise<void> }>;
  addListener(
    eventName: 'appState',
    listener: (event: { background: boolean }) => void,
  ): Promise<{ remove(): Promise<void> }>;
}

export interface BackgroundSession {
  /** Starts the foreground service on the first call, then keeps the notification up to date. */
  sync(state: NotificationState): void;
  stop(): void;
  onAction(handler: (action: BackgroundAction, source?: BackgroundActionSource) => void): Promise<() => void>;
  /**
   * Whether the app is in the background. On Android this is the activity state reported by the plugin,
   * because the plugin keeps the WebView looking visible and `document.hidden` can't be trusted; elsewhere
   * it is `document.hidden`.
   */
  isBackground(): boolean;
  /** Starts tracking the native app state. Safe to call on any platform and with older native builds. */
  watchAppState(): Promise<void>;
  /** Resolves once every queued native call has finished. */
  idle(): Promise<void>;
}

export function createBackgroundSession(
  plugin: BackgroundSessionPlugin,
  enabled: boolean,
  isDocumentHidden: () => boolean = () => document.hidden,
): BackgroundSession {
  let running = false;
  let nativeBackground = false;
  let sawAppStateEvent = false; // a live event is newer than a getState() answer that was still in flight
  let generation = 0; // bumped by stop() so a stale failed start can't clobber a newer one
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
        const started = generation;
        // If the service fails to start, forget it so the next sync tries again instead of updating nothing.
        enqueue(() => plugin.start(state).catch((error) => {
          if (started === generation) running = false;
          throw error;
        }));
      }
    },
    stop() {
      if (!enabled) return;
      running = false;
      generation += 1;
      enqueue(() => plugin.stop());
    },
    async onAction(handler) {
      if (!enabled) return () => {};
      try {
        const handle = await plugin.addListener('action', (event) => handler(event.action, event.source));
        return () => { void handle.remove().catch(() => {}); };
      } catch {
        return () => {};
      }
    },
    isBackground: () => (enabled ? nativeBackground : isDocumentHidden()),
    async watchAppState() {
      if (!enabled) return;
      try {
        await plugin.addListener('appState', (event) => {
          sawAppStateEvent = true;
          nativeBackground = event.background;
        });
      } catch {
        return; // older native build: stay on "foreground"
      }
      try {
        const state = await plugin.getState?.();
        if (state && !sawAppStateEvent) nativeBackground = state.background;
      } catch {
        // getState is optional
      }
    },
    idle: () => queue,
  };
}

export const backgroundSession = createBackgroundSession(
  registerPlugin<BackgroundSessionPlugin>('BackgroundSession'),
  usingNativeSpeech(),
);
