import { describe, expect, it } from 'vitest';
import { hasSpokenText } from './matching';

describe('hasSpokenText', () => {
  it('is false when recognition returned nothing', () => {
    expect(hasSpokenText([])).toBe(false);
  });

  it('is false when every transcript is blank or whitespace', () => {
    expect(hasSpokenText(['', '   ', '\n\t'])).toBe(false);
  });

  it('is true when any transcript has text', () => {
    expect(hasSpokenText(['', 'gato'])).toBe(true);
  });
});
