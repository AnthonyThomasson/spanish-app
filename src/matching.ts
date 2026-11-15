import type { WordKind } from './types';

const leadingArticles = /^(?:el|la|los|las|un|una|the|a|an|to)\s+/;

export function normalizeAnswer(value: string): string {
  let normalized = value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[¿?¡!.,;:"'()\-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  let previous = '';
  while (normalized !== previous) {
    previous = normalized;
    normalized = normalized.replace(leadingArticles, '');
  }
  return normalized.trim();
}

export function answerAlternatives(answer: string): string[] {
  const alternatives = answer
    .split(/\s*(?:;|\/|\s+or\s+|\s*,\s*)\s*/i)
    .flatMap((part) => [part, part.replace(/\([^)]*\)/g, '')])
    .map(normalizeAnswer)
    .filter(Boolean);
  return [...new Set(alternatives)];
}

/** Spanish subject pronouns, folded to one spelling each. Usted/Ud. and ustedes/Uds. are the same word; nosotras is nosotros. */
const subjectPronouns: Record<string, string> = {
  yo: 'yo', vos: 'vos', el: 'el', ella: 'ella',
  usted: 'ud', ud: 'ud', nosotros: 'nosotros', nosotras: 'nosotros',
  ellos: 'ellos', ellas: 'ellas', ustedes: 'uds', uds: 'uds',
};

const TOLERANCE_MIN_WORDS = 6;
const MAX_PARENTHETICALS = 4;

function expandContractions(text: string): string {
  return text
    .replace(/[\u2018\u2019`]/g, "'")
    .replace(/\bcan't\b/g, 'can not')
    .replace(/\bcannot\b/g, 'can not')
    .replace(/\bwon't\b/g, 'will not')
    .replace(/\b(\w+)n't\b/g, '$1 not')
    .replace(/\bi'm\b/g, 'i am')
    .replace(/\b(he|she|it)'s\b/g, '$1 is')
    .replace(/\b(we|they|you)'re\b/g, '$1 are')
    .replace(/\b(i|we|they|you)'ve\b/g, '$1 have')
    .replace(/\b(i|he|she|it|we|they|you)'ll\b/g, '$1 will');
}

/** Lowercase, accent-free words. Unlike a word card, a sentence keeps its articles. */
function sentenceTokens(text: string): string[] {
  return expandContractions(text.toLocaleLowerCase())
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);
}

/** Every reading of an answer with each parenthetical either said or left out, e.g. "you (formal) think". */
function parentheticalVariants(text: string): string[] {
  const groups = text.match(/\([^)]*\)/g) ?? [];
  if (!groups.length) return [text];
  const masks = groups.length <= MAX_PARENTHETICALS ? 2 ** groups.length : 0;
  const variants: string[] = [];
  const build = (keep: (index: number) => boolean) => {
    let index = 0;
    variants.push(text.replace(/\(([^)]*)\)/g, (_, inner: string) => keep(index++) ? inner : ''));
  };
  if (masks) {
    for (let mask = 0; mask < masks; mask++) build((index) => Boolean(mask & (1 << index)));
  } else {
    build(() => true);
    build(() => false);
  }
  return variants;
}

interface Reading {
  pronoun: string | null;
  rest: string[];
  length: number;
}

function reading(tokens: string[]): Reading {
  const pronoun = tokens.length > 1 ? subjectPronouns[tokens[0]] : undefined;
  return pronoun ? { pronoun, rest: tokens.slice(1), length: tokens.length } : { pronoun: null, rest: tokens, length: tokens.length };
}

/** True when the two word lists differ by at most one inserted, deleted or substituted word. */
function withinOneWord(a: string[], b: string[]): boolean {
  if (Math.abs(a.length - b.length) > 1) return false;
  let start = 0;
  while (start < a.length && start < b.length && a[start] === b[start]) start += 1;
  let endA = a.length;
  let endB = b.length;
  while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) { endA -= 1; endB -= 1; }
  return Math.max(endA - start, endB - start) <= 1;
}

function sentenceAlternatives(expected: string): Reading[] {
  return expected
    .split(/\s+\/\s+/)
    .flatMap(parentheticalVariants)
    .map((variant) => reading(sentenceTokens(variant)))
    .filter((alternative) => alternative.length > 0);
}

function isCorrectSentence(spoken: string, expected: string): boolean {
  const actual = reading(sentenceTokens(spoken));
  if (!actual.length) return false;
  return sentenceAlternatives(expected).some((alternative) => {
    if (actual.pronoun && alternative.pronoun && actual.pronoun !== alternative.pronoun) return false;
    const exact = actual.rest.length === alternative.rest.length && actual.rest.every((word, index) => word === alternative.rest[index]);
    return exact || (alternative.length >= TOLERANCE_MIN_WORDS && withinOneWord(actual.rest, alternative.rest));
  });
}

/**
 * Whether a spoken answer matches the expected one. Words take any of several alternatives. Sentences and
 * conjugations are matched on whole phrases, so commas and "or" stay part of the answer, and they forgive
 * a spoken or missing subject pronoun, English contractions, parentheticals and (in long sentences) one slip.
 */
export function isCorrectAnswer(spoken: string, expected: string, kind: WordKind = 'word'): boolean {
  if (kind !== 'word') return isCorrectSentence(spoken, expected);
  const actual = normalizeAnswer(spoken);
  if (!actual) return false;
  return answerAlternatives(expected).some((alternative) => alternative === actual);
}

/** Whether recognition returned anything to judge: blank or whitespace-only results are silence, not a wrong answer. */
export function hasSpokenText(transcripts: string[]): boolean {
  return transcripts.some((transcript) => transcript.trim() !== '');
}
