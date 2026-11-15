import { describe, expect, it, vi } from 'vitest';
import { dispatchBackgroundAction, type SessionControls } from './session-actions';

function controls(overrides: Partial<SessionControls> = {}): SessionControls {
  return {
    isActive: () => true,
    isPaused: () => false,
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
});
