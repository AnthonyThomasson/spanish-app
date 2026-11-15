import { describe, expect, it, vi } from 'vitest';
import { ensureMicrophonePermission } from './microphone';

describe('ensureMicrophonePermission', () => {
  it('returns true when granted', async () => {
    expect(await ensureMicrophonePermission(vi.fn(async () => ({ speechRecognition: 'granted' })))).toBe(true);
  });

  it('returns false when denied', async () => {
    expect(await ensureMicrophonePermission(vi.fn(async () => ({ speechRecognition: 'denied' })))).toBe(false);
  });

  it('never throws', async () => {
    expect(await ensureMicrophonePermission(vi.fn(async () => { throw new Error('nope'); }))).toBe(false);
  });
});
