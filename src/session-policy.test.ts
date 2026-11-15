import { describe, expect, it } from 'vitest';
import { shouldAutoPauseWhenHidden } from './session-policy';

const hiddenAuto = { hidden: true, active: true, mode: 'auto' as const, paused: false, native: false };

describe('shouldAutoPauseWhenHidden', () => {
  it('pauses a hidden hands-free session in the browser', () => {
    expect(shouldAutoPauseWhenHidden(hiddenAuto)).toBe(true);
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, mode: 'answer' })).toBe(true);
  });

  it('never pauses on native Android, where the foreground service keeps the session alive', () => {
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, native: true })).toBe(false);
  });

  it('does nothing when visible, inactive, flip mode, or already paused', () => {
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, hidden: false })).toBe(false);
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, active: false })).toBe(false);
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, mode: 'flip' })).toBe(false);
    expect(shouldAutoPauseWhenHidden({ ...hiddenAuto, paused: true })).toBe(false);
  });
});
