import type { WordKind } from './types';

/**
 * What the voice should say for a card's text. Only conjugation cards are touched: their parentheticals
 * ("(m.)", "(formal)", "(sentarse)") are notes that disambiguate the prompt and are optional when answering,
 * so they are left out, and the ' / ' between alternatives ("I am able / I can") is spoken as a pause.
 * Word and sentence parentheticals ("(male)", "(all)") carry meaning and are spoken as written. If nothing
 * would be left of a conjugation card, it is spoken as written.
 */
export function spokenText(text: string, kind: WordKind = 'word'): string {
  if (kind !== 'conjugation') return text;
  const spoken = text
    .replace(/\s*\([^)]*\)/g, '')
    .replace(/\s+\/\s+/g, ', ')
    .replace(/\s{2,}/g, ' ')
    .trim();
  return spoken || text;
}
