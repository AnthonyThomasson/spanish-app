import { describe, expect, it } from 'vitest';
import { spokenText } from './spoken-text';

describe('spokenText', () => {
  it('leaves out parenthetical notes', () => {
    expect(spokenText('they (m.) think')).toBe('they think');
    expect(spokenText('you (formal) think')).toBe('you think');
    expect(spokenText('yo me siento (sentarse)')).toBe('yo me siento');
    expect(spokenText('I am (estar)')).toBe('I am');
  });

  it('handles a note in the middle, several notes and a trailing note after an alternative', () => {
    expect(spokenText('to put (nail) polish on')).toBe('to put polish on');
    expect(spokenText('they (f.) do (hacer) / they (f.) make (hacer)')).toBe('they do / they make');
    expect(spokenText('I do / I make (hacer)')).toBe('I do / I make');
  });

  it('keeps text without parentheses exactly as it is', () => {
    expect(spokenText('ella piensa')).toBe('ella piensa');
    expect(spokenText('¿Cómo estás?')).toBe('¿Cómo estás?');
  });

  it('speaks the text as written when only a parenthetical would be left', () => {
    expect(spokenText('(m.)')).toBe('(m.)');
  });
});
