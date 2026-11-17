import { canonicalizeNumbers, numberValue, type NumberLanguage } from './numbers';
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
/**
 * The only words a long sentence may gain or lose, never as its first word. Spanish definite articles, object
 * pronouns (lo, la, le...) and unos/unas are left out on purpose: swapping or dropping them changes gender,
 * object or meaning. Pronouns, verb forms, numbers, negations and content words must always match.
 */
const FUNCTION_WORDS = new Set(['a', 'an', 'the', 'to', 'that', 'of', 'de', 'que', 'un', 'una']);
const MAX_PARENTHETICALS = 4;

function expandContractions(text: string): string {
  return text
    .replace(/[\u2018\u2019`]/g, "'")
    .replace(/\bcan't\b/g, 'can not')
    .replace(/\bcannot\b/g, 'can not')
    .replace(/\bwon't\b/g, 'will not')
    .replace(/\blet's\b/g, 'let us')
    .replace(/\by'?all\b/g, 'you all')
    .replace(/\byou guys\b/g, 'you all')
    .replace(/\b(\w+)n't\b/g, '$1 not')
    .replace(/\bi'm\b/g, 'i am')
    .replace(/\b(he|she|it|that|there|here|where|who|what|how)'s\b/g, '$1 is')
    .replace(/\b(we|they|you)'re\b/g, '$1 are')
    .replace(/\b(i|we|they|you)'ve\b/g, '$1 have')
    .replace(/\b(i|he|she|it|we|they|you)'ll\b/g, '$1 will')
    // 'd is "would" or "had"; only the polite forms are unambiguous.
    .replace(/\b(i|he|she|it|we|they|you)'d (?=like\b|love\b|prefer\b|rather\b)/g, '$1 would ');
}

/** Lowercase, accent-free words. Unlike a word card, a sentence keeps its articles. */
function sentenceTokens(text: string, language?: NumberLanguage): string[] {
  const tokens = expandContractions(text.toLocaleLowerCase().replace(/(\d),(?=\d{3}\b)/g, '$1'))
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);
  return canonicalizeNumbers(tokens, language);
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
  /** Every token, with a leading subject pronoun folded to one spelling. */
  tokens: string[];
  pronoun: string | null;
}

function reading(text: string, language?: NumberLanguage): Reading {
  const tokens = sentenceTokens(text, language);
  let pronoun = tokens.length > 1 ? subjectPronouns[tokens[0]] ?? null : null;
  // An unaccented "el" is the article, not "él": only the accented form may be dropped as a pronoun.
  if (pronoun === 'el' && !/^[^\p{L}]*él(?![\p{L}])/u.test(text.normalize('NFC').toLocaleLowerCase())) pronoun = null;
  if (pronoun) tokens[0] = pronoun;
  return { tokens, pronoun };
}

const sameWords = (a: string[], b: string[]) => a.length === b.length && a.every((word, index) => word === b[index]);

/** True when one list is the other plus a single small function word that is not the first word. */
function differsByFunctionWord(a: string[], b: string[]): boolean {
  const [shorter, longer] = a.length < b.length ? [a, b] : [b, a];
  if (longer.length - shorter.length !== 1) return false;
  let start = 0;
  while (start < shorter.length && shorter[start] === longer[start]) start += 1;
  return start > 0 && FUNCTION_WORDS.has(longer[start]) && sameWords(shorter.slice(start), longer.slice(start + 1));
}

function sentenceAlternatives(expected: string, language?: NumberLanguage): Reading[] {
  return expected
    .split(/\s+\/\s+(?![^()]*\))/) // a " / " inside parentheses stays part of the parenthetical
    .flatMap(parentheticalVariants)
    .map((variant) => reading(variant, language))
    .filter((alternative) => alternative.tokens.length > 0);
}

/**
 * How a prompt addressed to Ud. or Uds. starts ("Formal: Where are you from?", "Formal: you are"); a plain "you"
 * is vos. scripts/sentence_disambiguation.py and scripts/conjugation_english.py write it. It is optional when
 * answering, and may also be said.
 */
const ADDRESSEE_LABEL = /^\s*(Formal|Plural):\s*/i;

function withoutAddresseeLabel(expected: string, actual: Reading): [string, Reading] {
  const label = ADDRESSEE_LABEL.exec(expected);
  if (!label) return [expected, actual];
  const rest = expected.slice(label[0].length);
  if (actual.tokens[0] !== label[1].toLowerCase() || actual.tokens.length < 2) return [rest, actual];
  const tokens = actual.tokens.slice(1);
  const pronoun = subjectPronouns[tokens[0]] && tokens.length > 1 ? subjectPronouns[tokens[0]] : null;
  return [rest, { tokens, pronoun }];
}

function isCorrectSentence(spoken: string, expectedText: string, language?: NumberLanguage): boolean {
  const [expected, actual] = withoutAddresseeLabel(expectedText, reading(spoken, language));
  if (!actual.tokens.length) return false;
  return sentenceAlternatives(expected, language).some((alternative) => {
    const a = actual.tokens;
    const e = alternative.tokens;
    if (sameWords(a, e)) return true;
    // A subject pronoun is optional, but only when everything after it is identical.
    if (actual.pronoun && !alternative.pronoun && sameWords(a.slice(1), e)) return true;
    if (alternative.pronoun && !actual.pronoun && sameWords(a, e.slice(1))) return true;
    // Whole-list comparison, so a pronoun can never hide a swapped article or object pronoun.
    return e.length >= TOLERANCE_MIN_WORDS && differsByFunctionWord(a, e);
  });
}

/**
 * Whether a spoken answer matches the expected one. Words take any of several alternatives. Sentences and
 * conjugations are matched on whole phrases, so commas and "or" stay part of the answer, and they forgive
 * a spoken or missing subject pronoun, English contractions, parentheticals, digits for number words, and
 * (in long sentences) a missing or extra small function word. Words also accept a number said as digits.
 * `language` is the language of the expected answer; it decides whether "once" is a number.
 */
export function isCorrectAnswer(spoken: string, expected: string, kind: WordKind = 'word', language?: NumberLanguage): boolean {
  if (kind !== 'word') return isCorrectSentence(spoken, expected, language);
  const actual = normalizeAnswer(spoken);
  if (!actual) return false;
  const alternatives = answerAlternatives(expected);
  if (alternatives.some((alternative) => alternative === actual)) return true;
  // A recognizer often returns "2" for "two" (or "two" for a card that says 2), so digits meet number words.
  // Two number words never match by value: "once" (an English word) must not accept "eleven", nor "diez" accept "ten".
  const said = numberValue(actual, language);
  if (said === null) return false;
  const saidDigits = /^\d+$/.test(actual);
  return alternatives.some((alternative) => numberValue(alternative, language) === said && (saidDigits || /^\d+$/.test(alternative)));
}

/** Whether recognition returned anything to judge: blank or whitespace-only results are silence, not a wrong answer. */
export function hasSpokenText(transcripts: string[]): boolean {
  return transcripts.some((transcript) => transcript.trim() !== '');
}
