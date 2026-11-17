import type { WordKind } from './types';

/** The tags scripts/sentence_disambiguation.py adds. Keep this list in step with that module. */
const DISAMBIGUATION_TAG =
  /\s*\((?:m\.|f\.|preterit|imperfect|pronoun before|pronoun attached|Sp\. [^()]+)\)(?=[.?!"”'’)]*(?:\s+\/\s+|$))/g;

/** "Ud." and "Uds." are written abbreviations; a voice may spell them out, so they are said as words. */
function expandAbbreviations(text: string): string {
  return text.replace(/\bUds\.(?=\s|[,;:?!)]|$)/g, 'ustedes').replace(/\bUd\.(?=\s|[,;:?!)]|$)/g, 'usted');
}

/**
 * What the voice should say for a card's text. A conjugation card's parentheticals
 * ("(m.)", "(estar)", "(sentarse)") are notes that disambiguate the prompt and are optional when answering,
 * so they are left out, and the ' / ' between alternatives ("I am able / I can") is spoken as a pause.
 * Word parentheticals ("(male)", "(all)") and a sentence's own ("(tastes)", "(o'clock)") carry meaning and are
 * spoken as written. A sentence card's English may end in a tag added by the extractor to tell apart cards that
 * share a prompt ("I want to help them (m.).", "It was good (Sp. fue buena)."); that tag is a note for the
 * reader, so it is left out. A formal or plural prompt starts with a label ("Formal: Where are you from?"),
 * which is spoken: it is how the learner knows to answer with Ud. or Uds. instead of vos. "Ud." and "Uds."
 * are said as "usted" and "ustedes". If nothing would be left, the text is spoken as written.
 */
export function spokenText(written: string, kind: WordKind = 'word'): string {
  const text = expandAbbreviations(written);
  if (kind === 'sentence') return text.replace(DISAMBIGUATION_TAG, '').trim() || text;
  if (kind !== 'conjugation') return text;
  const spoken = text
    .replace(/\s*\([^)]*\)/g, '')
    .replace(/\s+\/\s+/g, ', ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return spoken || text;
}
