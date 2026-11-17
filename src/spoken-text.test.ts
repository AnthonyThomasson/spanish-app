import { describe, expect, it } from 'vitest';
import { spokenText } from './spoken-text';

describe('spokenText for conjugation cards', () => {
  it('leaves out parenthetical notes', () => {
    expect(spokenText('they (m.) think', 'conjugation')).toBe('they think');
    expect(spokenText('Formal: you think (pensar)', 'conjugation')).toBe('Formal: you think');
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

describe('spokenText for sentence cards with a disambiguation tag', () => {
  it('leaves out the tag before the closing punctuation', () => {
    expect(spokenText('I want to call them (m.).', 'sentence')).toBe('I want to call them.');
    expect(spokenText('I want to call them (f.).', 'sentence')).toBe('I want to call them.');
    expect(spokenText('I painted the fence (preterit).', 'sentence')).toBe('I painted the fence.');
    expect(spokenText('I was painting the fence (imperfect).', 'sentence')).toBe('I was painting the fence.');
    expect(spokenText('She is going to lend it to him (pronoun before).', 'sentence')).toBe('She is going to lend it to him.');
    expect(spokenText('She is going to lend it to him (pronoun attached).', 'sentence')).toBe('She is going to lend it to him.');
    expect(spokenText('The party was lively (Sp. fue).', 'sentence')).toBe('The party was lively.');
    expect(spokenText('It was cold (Sp. fue frío)', 'sentence')).toBe('It was cold');
  });

  it('leaves out the tag of every alternative of a merged card', () => {
    expect(spokenText('I see them (m.). / I watch them (m.).', 'sentence')).toBe('I see them. / I watch them.');
  });

  it('speaks the formal and plural labels, which say how to answer', () => {
    expect(spokenText('Formal: Where are you from?', 'sentence')).toBe('Formal: Where are you from?');
    expect(spokenText("Plural: Don't yell.", 'sentence')).toBe("Plural: Don't yell.");
  });

  it("keeps a sentence's own parentheticals, which carry meaning", () => {
    expect(spokenText('The tea is (tastes) sweet.', 'sentence')).toBe('The tea is (tastes) sweet.');
    expect(spokenText("Ten (minutes) past four (o'clock).", 'sentence')).toBe("Ten (minutes) past four (o'clock).");
  });

  it('does not strip a tag from a word card, which keeps "(male)" and the like', () => {
    expect(spokenText('the artist (m.)', 'word')).toBe('the artist (m.)');
  });

  it('speaks the text as written when only the tag would be left', () => {
    expect(spokenText('(m.)', 'sentence')).toBe('(m.)');
  });
});

describe('spokenText for Ud. and Uds.', () => {
  it('says the abbreviations as words on every kind of card', () => {
    expect(spokenText('¿De dónde es Ud.?', 'sentence')).toBe('¿De dónde es usted?');
    expect(spokenText('No griten Uds.', 'sentence')).toBe('No griten ustedes');
    expect(spokenText('Ud. está', 'conjugation')).toBe('usted está');
    expect(spokenText('Uds. son', 'conjugation')).toBe('ustedes son');
    expect(spokenText('Ud., Uds.')).toBe('usted, ustedes');
  });

  it('leaves words that only start the same alone', () => {
    expect(spokenText('Udine', 'word')).toBe('Udine');
  });
});
