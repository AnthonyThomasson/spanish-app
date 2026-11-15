import { describe, expect, it } from 'vitest';
import { buildNotification } from './notification';

const base = { mode: 'auto' as const, index: 11, total: 80, prompt: 'la casa', answer: 'the house', revealed: false, paused: false };

describe('buildNotification', () => {
  it('shows the mode and one-based progress in the title', () => {
    expect(buildNotification(base).title).toBe('Auto listen · 12 / 80');
    expect(buildNotification({ ...base, mode: 'answer' }).title).toBe('Speak answers · 12 / 80');
  });

  it('shows only the prompt until the answer is revealed', () => {
    expect(buildNotification(base).text).toBe('la casa');
  });

  it('adds the answer once revealed', () => {
    expect(buildNotification({ ...base, revealed: true }).text).toBe('la casa → the house');
  });

  it('carries the paused flag and the mode through', () => {
    expect(buildNotification({ ...base, paused: true })).toMatchObject({ paused: true, mode: 'auto' });
    expect(buildNotification({ ...base, mode: 'answer' }).mode).toBe('answer');
  });

  it('shows a failure notice instead of the card text while paused', () => {
    const state = buildNotification({ ...base, paused: true, notice: 'Microphone blocked — press Resume' });
    expect(state.text).toBe('Microphone blocked — press Resume');
    expect(state.paused).toBe(true);
  });

  it('ignores a failure notice once the session is running again', () => {
    expect(buildNotification({ ...base, revealed: true, notice: 'old failure' }).text).toBe('la casa → the house');
    expect(buildNotification({ ...base, notice: null }).text).toBe('la casa');
  });
});
