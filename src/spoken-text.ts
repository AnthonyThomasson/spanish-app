import type { WordKind } from './types';

/** The tags scripts/sentence_disambiguation.py adds. Keep this list in step with that module. */
const DISAMBIGUATION_TAG =
  /\s*\((?:vos|Ud\.|Uds\.|m\.|f\.|preterit|imperfect|pronoun before|pronoun attached|Sp\. [^()]+)\)(?=[.?!"”'’)]*$)/;

/**
 * What the voice should say for a card's text. Only conjugation cards are touched: their parentheticals
 * ("(m.)", "(formal)", "(sentarse)") are notes that disambiguate the prompt and are optional when answering,
 * so they are left out, and the ' / ' between alternatives ("I am able / I can") is spoken as a pause.
 * Word parentheticals ("(male)", "(all)") and a sentence's own ("(tastes)", "(o'clock)") carry meaning and are
 * spoken as written. A sentence card's English may end in a tag added by the extractor to tell apart cards that
 * share a prompt ("Drink (vos).", "I want to help them (m.).", "It was good (Sp. fue buena)."); that tag is a
 * note for the reader, so it is left out. If nothing would be left, the text is spoken as written.
 */
export function spokenText(text: string, kind: WordKind = 'word'): string {
  if (kind === 'sentence') return text.replace(DISAMBIGUATION_TAG, '').trim() || text;
  if (kind !== 'conjugation') return text;
  const spoken = text
    .replace(/\s*\([^)]*\)/g, '')
    .replace(/\s+\/\s+/g, ', ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return spoken || text;
}
