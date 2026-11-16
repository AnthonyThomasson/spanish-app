import { describe, expect, it } from 'vitest';
import {
  allHiddenMessage,
  formatChapterCount,
  formatHiddenDate,
  formatSelectionSummary,
  pluralize,
} from './format';

describe('pluralize', () => {
  it('uses the singular for exactly one', () => {
    expect(pluralize(1, 'word')).toBe('1 word');
  });

  it('uses the plural otherwise, including zero', () => {
    expect(pluralize(0, 'word')).toBe('0 words');
    expect(pluralize(42, 'word')).toBe('42 words');
  });

  it('accepts an irregular plural', () => {
    expect(pluralize(2, 'try', 'tries')).toBe('2 tries');
  });
});

describe('formatChapterCount', () => {
  it('shows only the card count when nothing is hidden', () => {
    expect(formatChapterCount(42, 0)).toBe('42 cards');
  });

  it('adds the hidden count when some cards are hidden', () => {
    expect(formatChapterCount(42, 12)).toBe('42 cards · 12 hidden');
  });

  it('handles every card hidden and a single-card chapter', () => {
    expect(formatChapterCount(5, 5)).toBe('5 cards · 5 hidden');
    expect(formatChapterCount(1, 0)).toBe('1 card');
  });
});

describe('formatSelectionSummary', () => {
  it('counts chapters and the cards that will be asked', () => {
    expect(formatSelectionSummary(3, 120)).toBe('3 chapters · 120 cards');
  });

  it('uses singular forms', () => {
    expect(formatSelectionSummary(1, 1)).toBe('1 chapter · 1 card');
  });

  it('shows zero cards', () => {
    expect(formatSelectionSummary(0, 0)).toBe('0 chapters · 0 cards');
  });
});

describe('formatHiddenDate', () => {
  // Built from local date parts so the result does not depend on the machine's time zone.
  const noon = new Date(2026, 11, 6, 12, 0, 0).getTime();

  it('formats a readable local date with the year', () => {
    expect(formatHiddenDate(noon, 'en-US')).toBe('December 6, 2026');
  });

  it('uses the local calendar day, not UTC', () => {
    const lateEvening = new Date(2026, 0, 31, 23, 30, 0).getTime();
    expect(formatHiddenDate(lateEvening, 'en-US')).toBe('January 31, 2026');
  });
});

describe('allHiddenMessage', () => {
  it('names the earliest date the cards come back', () => {
    const noon = new Date(2026, 11, 6, 12, 0, 0).getTime();
    expect(allHiddenMessage(noon, 'en-US')).toBe('All these cards are hidden until December 6, 2026.');
  });
});
