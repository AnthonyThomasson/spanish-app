import { describe, expect, it } from 'vitest';
import { spokenText } from './spoken-text';

describe('spokenText for conjugation cards', () => {
  it('leaves out parenthetical notes', () => {
    expect(spokenText('they (m.) think', 'conjugation')).toBe('they think');
    expect(spokenText('you (formal) think', 'conjugation')).toBe('you think');
    expect(spokenText('yo me siento (sentarse)', 'conjugation')).toBe('yo me siento');
    expect(spokenText('I am (estar)', 'conjugation')).toBe('I am');
  });

  it('speaks alternatives separated by a comma and drops the note after the last one', () => {
    expect(spokenText('I am able / I can', 'conjugation')).toBe('I am able, I can');
    expect(spokenText('they (f.) do / they (f.) make (hacer)', 'conjugation')).toBe('they do, they make');
    expect(spokenText('I do / I make (hacer)', 'conjugation')).toBe('I do, I make');
  });

  it('keeps plain conjugation text as it is', () => {
    expect(spokenText('ella piensa', 'conjugation')).toBe('ella piensa');
  });

  it('speaks the text as written when only a parenthetical would be left', () => {
    expect(spokenText('(m.)', 'conjugation')).toBe('(m.)');
  });
});

describe('spokenText for other cards', () => {
  it('keeps the parentheticals of a word card, so its meaning is not lost', () => {
    expect(spokenText('the artist (male)')).toBe('the artist (male)');
    expect(spokenText('the artist (female)', 'word')).toBe('the artist (female)');
    expect(spokenText('it to you (all)', 'word')).toBe('it to you (all)');
  });

  it('keeps sentences and slashes as written', () => {
    expect(spokenText('Do you (all) want it?', 'sentence')).toBe('Do you (all) want it?');
    expect(spokenText('the husband / the wife', 'word')).toBe('the husband / the wife');
  });
});
