import { describe, expect, it } from 'vitest';
import {
  createProgress,
  directionsFor,
  DEFAULT_SETTINGS,
  STORAGE_KEY,
  WEEK_MS,
  type StorageLike,
} from './progress';
import type { Chapter, Word } from './types';

const word = (spanish: string, english: string): Word => ({ spanish, english, sourcePage: 1 });
const gato = word('el gato', 'the cat');
const perro = word('el perro', 'the dog');
const casa = word('la casa', 'the house');

const chapter1: Chapter = { number: 1, title: 'One', words: [gato, perro] };
const chapter2: Chapter = { number: 2, title: 'Two', words: [casa] };

function memoryStorage(initial: Record<string, string> = {}): StorageLike & { data: Record<string, string> } {
  const data = { ...initial };
  return {
    data,
    getItem: (key) => (key in data ? data[key] : null),
    setItem: (key, value) => {
      data[key] = value;
    },
  };
}

function setup(storage: StorageLike | null = memoryStorage()) {
  const clock = { now: 1_000_000 };
  const progress = createProgress({ storage, now: () => clock.now });
  return { clock, progress, storage };
}

describe('streaks', () => {
  it('counts consecutive correct answers', () => {
    const { progress } = setup();
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.streak(1, gato, 'es-en')).toBe(2);
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
  });

  it('resets on a miss, and a correct answer after a miss counts as 1', () => {
    const { progress } = setup();
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordMiss(1, gato, 'es-en');
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.streak(1, gato, 'es-en')).toBe(1);
  });

  it('keys words by chapter, Spanish and English', () => {
    const { progress } = setup();
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.streak(2, gato, 'es-en')).toBe(0);
    expect(progress.streak(1, word('el gato', 'the tomcat'), 'es-en')).toBe(0);
    expect(progress.streak(1, word('el gato', 'the cat'), 'es-en')).toBe(1);
  });
});

describe('mastering', () => {
  it('hides the word for the default 3 weeks after 3 correct in a row and resets the streak', () => {
    const { progress, clock } = setup();
    for (let i = 0; i < 3; i++) progress.recordCorrect(1, gato, 'es-en');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(clock.now + 3 * WEEK_MS);
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
  });

  it('honours a custom mastery count and period', () => {
    const { progress, clock } = setup();
    progress.updateSettings({ masterCount: 1, hideWeeks: 5 });
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(clock.now + 5 * WEEK_MS);
  });

  it('returns the word with a streak of 0 once the hidden period ends', () => {
    const { progress, clock } = setup();
    for (let i = 0; i < 3; i++) progress.recordCorrect(1, gato, 'es-en');
    clock.now += 3 * WEEK_MS - 1;
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
    clock.now += 1;
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBeNull();
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.streak(1, gato, 'es-en')).toBe(1);
  });
});

describe('Know it', () => {
  it('hides immediately for the configured period in that direction only', () => {
    const { progress, clock } = setup();
    progress.updateSettings({ hideWeeks: 2 });
    progress.knowIt(1, gato, 'en-es');
    expect(progress.hiddenUntil(1, gato, 'en-es')).toBe(clock.now + 2 * WEEK_MS);
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
  });
});

describe('Know it on an already hidden word', () => {
  it('never shortens the hide period', () => {
    const { progress, clock } = setup();
    progress.updateSettings({ hideWeeks: 10 });
    progress.knowIt(1, gato, 'es-en');
    const until = progress.hiddenUntil(1, gato, 'es-en');
    progress.updateSettings({ hideWeeks: 1 });
    clock.now += WEEK_MS;
    progress.knowIt(1, gato, 'es-en');
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(until);
  });

  it('extends the hide when the new period ends later', () => {
    const { progress, clock } = setup();
    progress.updateSettings({ hideWeeks: 1 });
    progress.knowIt(1, gato, 'es-en');
    progress.updateSettings({ hideWeeks: 4 });
    clock.now += WEEK_MS / 2;
    progress.knowIt(1, gato, 'es-en');
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(clock.now + 4 * WEEK_MS);
  });
});

describe('per-direction separation', () => {
  it('tracks streaks and hiding independently', () => {
    const { progress } = setup();
    for (let i = 0; i < 3; i++) progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'en-es');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
    expect(progress.isHidden(1, gato, 'en-es')).toBe(false);
    expect(progress.streak(1, gato, 'en-es')).toBe(1);
    progress.recordMiss(1, gato, 'en-es');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
  });
});

describe('reviewing hidden words', () => {
  it('does not extend or change the hidden period on a correct answer', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    const until = progress.hiddenUntil(1, gato, 'es-en');
    clock.now += WEEK_MS;
    for (let i = 0; i < 5; i++) progress.recordCorrect(1, gato, 'es-en');
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(until);
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
  });

  it('un-hides on a miss and resets the streak', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.recordMiss(1, gato, 'es-en');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
  });
});

describe('a miss on an expired hidden word', () => {
  it('leaves streak 0 and the word not hidden', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    clock.now += 3 * WEEK_MS;
    progress.recordMiss(1, gato, 'es-en');
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBeNull();
  });
});

describe('deck filtering', () => {
  it('leaves out hidden words in the chosen direction unless hidden words are included', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(2, casa, 'en-es');

    const esEn = progress.buildDeck([chapter1, chapter2], 'es-en', false);
    expect(esEn.map((card) => card.word)).toEqual([perro, casa]);
    expect(esEn.map((card) => card.chapter)).toEqual([1, 2]);
    expect(esEn[0].directions).toEqual(['es-en']);

    const enEs = progress.buildDeck([chapter1, chapter2], 'en-es', false);
    expect(enEs.map((card) => card.word)).toEqual([gato, perro]);

    const all = progress.buildDeck([chapter1, chapter2], 'es-en', true);
    expect(all.map((card) => card.word)).toEqual([gato, perro, casa]);
  });

  it('counts hidden words per chapter for a direction', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, perro, 'es-en');
    progress.knowIt(1, perro, 'en-es');
    expect(progress.hiddenCount(chapter1, 'es-en')).toBe(2);
    expect(progress.hiddenCount(chapter1, 'en-es')).toBe(1);
    expect(progress.hiddenCount(chapter2, 'es-en')).toBe(0);
  });

  it('counts only the cards that will be asked', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    expect(progress.cardCount([chapter1, chapter2], 'es-en', false)).toBe(2);
    expect(progress.cardCount([chapter1, chapter2], 'es-en', true)).toBe(3);
    expect(progress.cardCount([], 'es-en', false)).toBe(0);
  });

  it('reports the earliest hide-until date among the hidden words of a selection', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    clock.now += 1000;
    progress.knowIt(1, perro, 'es-en');
    progress.knowIt(2, casa, 'es-en');
    expect(progress.earliestHiddenUntil([chapter1, chapter2], 'es-en')).toBe(1_000_000 + 3 * WEEK_MS);
    expect(progress.earliestHiddenUntil([chapter2], 'es-en')).toBe(1_001_000 + 3 * WEEK_MS);
    expect(progress.earliestHiddenUntil([chapter1], 'en-es')).toBeNull();
  });

  it('ignores expired hides', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    clock.now += 3 * WEEK_MS;
    expect(progress.buildDeck([chapter1], 'es-en', false)).toHaveLength(2);
    expect(progress.hiddenCount(chapter1, 'es-en')).toBe(0);
    expect(progress.earliestHiddenUntil([chapter1], 'es-en')).toBeNull();
  });
});

describe('Both direction', () => {
  it('covers both card directions', () => {
    expect(directionsFor('both')).toEqual(['es-en', 'en-es']);
    expect(directionsFor('es-en')).toEqual(['es-en']);
  });

  it('offers only the directions that are not hidden', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, perro, 'en-es');
    const deck = progress.buildDeck([chapter1, chapter2], 'both', false);
    expect(deck.map((card) => [card.word, card.directions])).toEqual([
      [gato, ['en-es']],
      [perro, ['es-en']],
      [casa, ['es-en', 'en-es']],
    ]);
  });

  it('leaves out a word hidden in both directions, unless hidden words are included', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, gato, 'en-es');
    expect(progress.buildDeck([chapter1], 'both', false).map((card) => card.word)).toEqual([perro]);
    const included = progress.buildDeck([chapter1], 'both', true);
    expect(included.map((card) => card.word)).toEqual([gato, perro]);
    expect(included[0].directions).toEqual(['es-en', 'en-es']);
  });

  it('counts as hidden only the words hidden in both directions', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, perro, 'es-en');
    progress.knowIt(1, perro, 'en-es');
    expect(progress.hiddenCount(chapter1, 'both')).toBe(1);
    expect(progress.hiddenCount(chapter1, 'es-en')).toBe(2);
  });

  it('counts the cards that will actually be asked', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, perro, 'es-en');
    progress.knowIt(1, perro, 'en-es');
    expect(progress.cardCount([chapter1, chapter2], 'both', false)).toBe(2);
    expect(progress.cardCount([chapter1, chapter2], 'both', true)).toBe(3);
  });

  it('reports the earliest date at which any direction of any selected word comes back', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    clock.now += 1000;
    progress.knowIt(1, gato, 'en-es');
    clock.now += 1000;
    progress.knowIt(1, perro, 'es-en');
    progress.knowIt(1, perro, 'en-es');
    expect(progress.earliestHiddenUntil([chapter1], 'both')).toBe(1_000_000 + 3 * WEEK_MS);
    expect(progress.earliestHiddenUntil([chapter1], 'en-es')).toBe(1_001_000 + 3 * WEEK_MS);
  });

  it('keeps progress separate per card direction', () => {
    const { progress } = setup();
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'en-es');
    expect(progress.streak(1, gato, 'es-en')).toBe(2);
    expect(progress.streak(1, gato, 'en-es')).toBe(1);
  });
});

describe('resetChapter', () => {
  it('clears streaks and hidden dates in both directions for that chapter only', () => {
    const { progress } = setup();
    progress.knowIt(1, gato, 'es-en');
    progress.knowIt(1, gato, 'en-es');
    progress.recordCorrect(1, perro, 'es-en');
    progress.knowIt(2, casa, 'es-en');
    progress.resetChapter(1);
    expect(progress.isHidden(1, gato, 'es-en')).toBe(false);
    expect(progress.isHidden(1, gato, 'en-es')).toBe(false);
    expect(progress.streak(1, perro, 'es-en')).toBe(0);
    expect(progress.isHidden(2, casa, 'es-en')).toBe(true);
  });

  it('does not touch chapters whose number shares a prefix', () => {
    const { progress } = setup();
    progress.knowIt(11, gato, 'es-en');
    progress.resetChapter(1);
    expect(progress.isHidden(11, gato, 'es-en')).toBe(true);
  });
});

describe('settings', () => {
  it('defaults to 3 correct answers and 3 weeks', () => {
    expect(setup().progress.settings()).toEqual({ masterCount: 3, hideWeeks: 3 });
    expect(DEFAULT_SETTINGS).toEqual({ masterCount: 3, hideWeeks: 3 });
  });

  it('clamps to 1-10 correct answers and 1-12 weeks, rounding and ignoring junk', () => {
    const { progress } = setup();
    expect(progress.updateSettings({ masterCount: 0, hideWeeks: 99 })).toEqual({ masterCount: 1, hideWeeks: 12 });
    expect(progress.updateSettings({ masterCount: 50, hideWeeks: -4 })).toEqual({ masterCount: 10, hideWeeks: 1 });
    expect(progress.updateSettings({ masterCount: 4.6 }).masterCount).toBe(5);
  });

  it('keeps the current value when a field is missing or not a number', () => {
    const { progress } = setup();
    progress.updateSettings({ masterCount: 5, hideWeeks: 6 });
    expect(progress.updateSettings({ masterCount: Number.NaN })).toEqual({ masterCount: 5, hideWeeks: 6 });
    expect(progress.updateSettings({ masterCount: undefined, hideWeeks: 7 })).toEqual({ masterCount: 5, hideWeeks: 7 });
  });

  it('applies to later hides only, leaving existing hide-until dates alone', () => {
    const { progress, clock } = setup();
    progress.knowIt(1, gato, 'es-en');
    const until = progress.hiddenUntil(1, gato, 'es-en');
    progress.updateSettings({ hideWeeks: 10 });
    expect(progress.hiddenUntil(1, gato, 'es-en')).toBe(until);
    progress.knowIt(1, perro, 'es-en');
    expect(progress.hiddenUntil(1, perro, 'es-en')).toBe(clock.now + 10 * WEEK_MS);
  });
});

describe('persistence', () => {
  it('saves and reloads progress and settings', () => {
    const storage = memoryStorage();
    const first = setup(storage);
    first.progress.updateSettings({ masterCount: 5, hideWeeks: 6 });
    first.progress.knowIt(1, gato, 'es-en');
    first.progress.recordCorrect(1, perro, 'en-es');

    const second = createProgress({ storage, now: () => first.clock.now });
    expect(second.settings()).toEqual({ masterCount: 5, hideWeeks: 6 });
    expect(second.isHidden(1, gato, 'es-en')).toBe(true);
    expect(second.streak(1, perro, 'en-es')).toBe(1);
  });

  it('drops expired hides from storage on the next save', () => {
    const storage = memoryStorage();
    const { progress, clock } = setup(storage);
    progress.knowIt(1, gato, 'es-en');
    clock.now += 3 * WEEK_MS;
    progress.recordCorrect(1, perro, 'es-en');
    const saved = JSON.parse(storage.data[STORAGE_KEY]);
    expect(Object.keys(saved.records)).toHaveLength(1);
  });

  it('saves a reset', () => {
    const storage = memoryStorage();
    const first = setup(storage);
    first.progress.knowIt(1, gato, 'es-en');
    first.progress.resetChapter(1);
    const second = createProgress({ storage, now: () => first.clock.now });
    expect(second.isHidden(1, gato, 'es-en')).toBe(false);
  });

  it('works in memory without saving when storage is missing', () => {
    const { progress } = setup(null);
    progress.updateSettings({ masterCount: 2 });
    progress.recordCorrect(1, gato, 'es-en');
    progress.recordCorrect(1, gato, 'es-en');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
  });

  it('works when saving throws (quota, private browsing)', () => {
    const storage: StorageLike = {
      getItem: () => null,
      setItem: () => {
        throw new Error('QuotaExceededError');
      },
    };
    const { progress } = setup(storage);
    expect(() => progress.knowIt(1, gato, 'es-en')).not.toThrow();
    expect(() => progress.updateSettings({ hideWeeks: 4 })).not.toThrow();
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
    expect(progress.settings().hideWeeks).toBe(4);
  });

  it('works when reading throws', () => {
    const storage: StorageLike = {
      getItem: () => {
        throw new Error('SecurityError');
      },
      setItem: () => {},
    };
    const { progress } = setup(storage);
    progress.knowIt(1, gato, 'es-en');
    expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
  });

  it.each([
    ['invalid JSON', '{not json'],
    ['a non-object', '42'],
    ['null', 'null'],
    ['wrong field types', JSON.stringify({ version: 1, settings: 'x', records: [1, 2] })],
    [
      'bad records',
      JSON.stringify({
        version: 1,
        settings: { masterCount: 'many', hideWeeks: 500 },
        records: { a: 'b', c: { streak: -2, hiddenUntil: 'soon' }, d: null },
      }),
    ],
  ])('starts fresh from corrupt saved data: %s', (_name, raw) => {
    const { progress } = setup(memoryStorage({ [STORAGE_KEY]: raw }));
    expect(progress.settings().masterCount).toBe(3);
    expect(progress.settings().hideWeeks).toBeLessThanOrEqual(12);
    expect(progress.streak(1, gato, 'es-en')).toBe(0);
    expect(() => progress.recordCorrect(1, gato, 'es-en')).not.toThrow();
    expect(progress.streak(1, gato, 'es-en')).toBe(1);
  });

  it('works when the global localStorage getter throws', () => {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      get() {
        throw new Error('SecurityError');
      },
    });
    try {
      const progress = createProgress();
      progress.knowIt(1, gato, 'es-en');
      expect(progress.isHidden(1, gato, 'es-en')).toBe(true);
    } finally {
      if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor);
      else delete (globalThis as { localStorage?: unknown }).localStorage;
    }
  });
});
