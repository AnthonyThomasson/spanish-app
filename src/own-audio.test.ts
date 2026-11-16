import { describe, expect, it } from 'vitest';
import { createOwnAudioGuard } from './own-audio';

function setup(graceMs = 2000) {
  let now = 1000;
  const guard = createOwnAudioGuard(() => now, graceMs);
  return { guard, advance: (ms: number) => { now += ms; } };
}

describe('createOwnAudioGuard', () => {
  it('is inactive until something plays', () => {
    expect(setup().guard.isActive()).toBe(false);
  });

  it('is active while our audio plays, however long', () => {
    const { guard, advance } = setup();
    guard.begin();
    advance(60_000);
    expect(guard.isActive()).toBe(true);
  });

  it('stays active for the grace period after audio ends, because focus changes arrive late', () => {
    const { guard, advance } = setup(2000);
    const end = guard.begin();
    end();
    advance(1999);
    expect(guard.isActive()).toBe(true);
    advance(2);
    expect(guard.isActive()).toBe(false);
  });

  it('counts overlapping audio: active until the last one ends', () => {
    const { guard, advance } = setup(1000);
    const first = guard.begin();
    const second = guard.begin();
    first();
    advance(5000);
    expect(guard.isActive()).toBe(true);
    second();
    expect(guard.isActive()).toBe(true);
    advance(1001);
    expect(guard.isActive()).toBe(false);
  });

  it('ignores a second call to the same end function', () => {
    const { guard, advance } = setup(1000);
    const first = guard.begin();
    guard.begin();
    first();
    first();
    advance(5000);
    expect(guard.isActive()).toBe(true);
  });

  it('touch starts a grace period without holding audio open', () => {
    const { guard, advance } = setup(1000);
    guard.touch();
    expect(guard.isActive()).toBe(true);
    advance(1001);
    expect(guard.isActive()).toBe(false);
  });
});
