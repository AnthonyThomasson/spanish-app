import { describe, expect, it, vi } from 'vitest';
import { dispatchBackgroundAction, type SessionControls } from './session-actions';

function controls(overrides: Partial<SessionControls> = {}): SessionControls {
  return {
    isActive: () => true,
    isPaused: () => false,
    isListening: () => false,
    isOwnAudio: () => false,
    pause: vi.fn(),
    resume: vi.fn(),
    skip: vi.fn(),
    stop: vi.fn(),
    ...overrides,
  };
}

describe('dispatchBackgroundAction', () => {
  it('pauses a running session', () => {
    const c = controls();
    dispatchBackgroundAction('pause', c);
    expect(c.pause).toHaveBeenCalledOnce();
  });

  it('does nothing when pausing an already paused session', () => {
    const c = controls({ isPaused: () => true });
    dispatchBackgroundAction('pause', c);
    expect(c.pause).not.toHaveBeenCalled();
  });

  it('resumes only a paused session', () => {
    const paused = controls({ isPaused: () => true });
    dispatchBackgroundAction('resume', paused);
    expect(paused.resume).toHaveBeenCalledOnce();
    const running = controls();
    dispatchBackgroundAction('resume', running);
    expect(running.resume).not.toHaveBeenCalled();
  });

  it('skips and stops', () => {
    const c = controls();
    dispatchBackgroundAction('skip', c);
    dispatchBackgroundAction('stop', c);
    expect(c.skip).toHaveBeenCalledOnce();
    expect(c.stop).toHaveBeenCalledOnce();
  });

  it('ignores every action when no session is active', () => {
    const c = controls({ isActive: () => false });
    (['pause', 'resume', 'skip', 'stop'] as const).forEach((action) => dispatchBackgroundAction(action, c));
    expect(c.pause).not.toHaveBeenCalled();
    expect(c.resume).not.toHaveBeenCalled();
    expect(c.skip).not.toHaveBeenCalled();
    expect(c.stop).not.toHaveBeenCalled();
  });

  it('ignores a transient audio-focus pause while our own speech or recognizer audio is active', () => {
    const c = controls({ isOwnAudio: () => true });
    dispatchBackgroundAction('pause', c, 'audio-focus', { focusChange: -2, transient: true, call: false });
    expect(c.pause).not.toHaveBeenCalled();
  });

  it('treats an audio-focus pause with no detail (older native build) as transient', () => {
    const c = controls({ isOwnAudio: () => true });
    dispatchBackgroundAction('pause', c, 'audio-focus');
    expect(c.pause).not.toHaveBeenCalled();
  });

  it('pauses on a permanent audio-focus loss even during our own audio or while listening', () => {
    const c = controls({ isOwnAudio: () => true, isListening: () => true });
    dispatchBackgroundAction('pause', c, 'audio-focus', { focusChange: -1, transient: false, call: false });
    expect(c.pause).toHaveBeenCalledOnce();
  });

  it('pauses when a call is ringing or in progress, even during our own audio', () => {
    const c = controls({ isOwnAudio: () => true, isListening: () => true });
    dispatchBackgroundAction('pause', c, 'audio-focus', { focusChange: -2, transient: true, call: true });
    expect(c.pause).toHaveBeenCalledOnce();
  });

  it('logs why a pause was ignored or honoured', () => {
    const info = vi.spyOn(console, 'info').mockImplementation(() => {});
    dispatchBackgroundAction('pause', controls({ isOwnAudio: () => true }), 'audio-focus', { focusChange: -2, transient: true, call: false });
    dispatchBackgroundAction('pause', controls(), 'notification');
    expect(info).toHaveBeenNthCalledWith(1, '[session] pause ignored source=audio-focus focusChange=-2 transient=true call=false listening=false ownAudio=true');
    expect(info).toHaveBeenNthCalledWith(2, '[session] pause pausing source=notification focusChange=n/a transient=n/a call=n/a listening=false ownAudio=false');
    info.mockRestore();
  });

  it('still pauses on an audio-focus loss when none of our audio is active', () => {
    const c = controls({ isOwnAudio: () => false });
    dispatchBackgroundAction('pause', c, 'audio-focus');
    expect(c.pause).toHaveBeenCalledOnce();
  });

  it('pauses on a notification Pause even while our own audio is active', () => {
    const c = controls({ isOwnAudio: () => true, isListening: () => true });
    dispatchBackgroundAction('pause', c, 'notification');
    expect(c.pause).toHaveBeenCalledOnce();
  });

  it('ignores an audio-focus pause while our own recognizer is listening', () => {
    const c = controls({ isListening: () => true });
    dispatchBackgroundAction('pause', c, 'audio-focus');
    expect(c.pause).not.toHaveBeenCalled();
  });

  it('honours an audio-focus pause when not listening, and notification pauses always', () => {
    const idle = controls();
    dispatchBackgroundAction('pause', idle, 'audio-focus');
    expect(idle.pause).toHaveBeenCalledOnce();
    const listening = controls({ isListening: () => true });
    dispatchBackgroundAction('pause', listening, 'notification');
    dispatchBackgroundAction('pause', listening);
    expect(listening.pause).toHaveBeenCalledTimes(2);
  });
});
