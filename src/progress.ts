import type { CardDirection, Chapter, Direction, Word } from './types';

/**
 * Per-word, per-direction progress: a streak of correct answers and an optional
 * "hidden until" timestamp. Words have no IDs, so they are keyed by chapter
 * number + Spanish + English.
 *
 * Rules:
 * - A correct answer adds 1 to the streak. Reaching `masterCount` hides the word
 *   for `hideWeeks` and resets the streak to 0.
 * - A miss (a wrong answer, which also reveals the answer) resets the streak to 0 and
 *   un-hides the word. Skip changes nothing, so there is no function for it.
 * - "Know it" hides the word right away; on an already hidden word it keeps the later of the
 *   existing and the new hide-until date, so it never shortens a hide.
 * - While a word is hidden (reviewed via "Include hidden words") a correct answer
 *   changes nothing, so it never extends the hidden period.
 * - Once `now >= hiddenUntil` the word counts as not hidden with streak 0.
 */

export const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
export const STORAGE_KEY = 'spanish-app:progress';

export interface ProgressSettings {
  /** Correct answers in a row needed to master a word (1-10). */
  masterCount: number;
  /** Weeks a mastered word stays hidden (1-12). */
  hideWeeks: number;
}

export const DEFAULT_SETTINGS: ProgressSettings = { masterCount: 3, hideWeeks: 3 };
const LIMITS = { masterCount: [1, 10], hideWeeks: [1, 12] } as const;

export interface DirectionRecord {
  streak: number;
  /** Epoch ms until which the word is hidden, or null. */
  hiddenUntil: number | null;
}

/** Minimal slice of the Web Storage API, so tests can inject a fake. */
export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface DeckCard {
  chapter: number;
  word: Word;
  /**
   * Directions this card may be asked in: the non-hidden directions of the
   * chosen direction(s), or all of them when hidden words are included.
   */
  directions: CardDirection[];
}

const EMPTY: Readonly<DirectionRecord> = Object.freeze({ streak: 0, hiddenUntil: null });

/** Card directions covered by a deck's direction choice; "Both" covers both. */
export function directionsFor(choice: Direction): CardDirection[] {
  return choice === 'both' ? ['es-en', 'en-es'] : [choice];
}

export function clampSettings(input: Partial<ProgressSettings> | null | undefined): ProgressSettings {
  const clamp = (value: unknown, [min, max]: readonly [number, number], fallback: number) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return fallback;
    return Math.min(max, Math.max(min, Math.round(value)));
  };
  return {
    masterCount: clamp(input?.masterCount, LIMITS.masterCount, DEFAULT_SETTINGS.masterCount),
    hideWeeks: clamp(input?.hideWeeks, LIMITS.hideWeeks, DEFAULT_SETTINGS.hideWeeks),
  };
}

// --- Pure record transitions (all take the current time explicitly) ---

/** The record as it counts at `now`: an expired hide becomes a fresh record. */
export function effectiveRecord(record: DirectionRecord | undefined, now: number): Readonly<DirectionRecord> {
  if (!record) return EMPTY;
  if (record.hiddenUntil !== null && now >= record.hiddenUntil) return EMPTY;
  return record;
}

export function isRecordHidden(record: DirectionRecord | undefined, now: number): boolean {
  return effectiveRecord(record, now).hiddenUntil !== null;
}

export function applyCorrect(
  record: DirectionRecord | undefined,
  settings: ProgressSettings,
  now: number,
): DirectionRecord {
  const current = effectiveRecord(record, now);
  if (current.hiddenUntil !== null) return current; // reviewing a hidden word
  const streak = current.streak + 1;
  if (streak >= settings.masterCount) return { streak: 0, hiddenUntil: now + settings.hideWeeks * WEEK_MS };
  return { streak, hiddenUntil: null };
}

export function applyMiss(): Readonly<DirectionRecord> {
  return EMPTY;
}

export function applyKnowIt(
  record: DirectionRecord | undefined,
  settings: ProgressSettings,
  now: number,
): DirectionRecord {
  // Never shorten an existing hide (e.g. after the period was lowered in settings).
  const existing = effectiveRecord(record, now).hiddenUntil ?? 0;
  return { streak: 0, hiddenUntil: Math.max(existing, now + settings.hideWeeks * WEEK_MS) };
}

// --- Store ---

export interface ProgressOptions {
  /** Storage to persist to; null for in-memory only. Defaults to localStorage when usable. */
  storage?: StorageLike | null;
  /** Clock, in epoch ms. Defaults to Date.now. */
  now?: () => number;
}

const SEP = '\u001f';
const chapterPrefix = (chapter: number) => `${chapter}${SEP}`;
const recordKey = (chapter: number, word: Pick<Word, 'spanish' | 'english'>, direction: CardDirection) =>
  `${chapterPrefix(chapter)}${word.spanish}${SEP}${word.english}${SEP}${direction}`;

function defaultStorage(): StorageLike | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null; // accessing localStorage can throw (blocked site data)
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function parseRecord(value: unknown): DirectionRecord | null {
  if (!isPlainObject(value)) return null;
  const { streak, hiddenUntil } = value;
  const validStreak = typeof streak === 'number' && Number.isInteger(streak) && streak >= 0;
  const validUntil = hiddenUntil === null || (typeof hiddenUntil === 'number' && Number.isFinite(hiddenUntil));
  if (!validStreak || !validUntil) return null;
  return { streak, hiddenUntil };
}

export function createProgress(options: ProgressOptions = {}) {
  const storage = options.storage === undefined ? defaultStorage() : options.storage;
  const clock = options.now ?? Date.now;

  let settings: ProgressSettings = { ...DEFAULT_SETTINGS };
  let records = new Map<string, DirectionRecord>();

  function load(): void {
    try {
      const raw = storage?.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed: unknown = JSON.parse(raw);
      if (!isPlainObject(parsed)) return;
      settings = clampSettings(isPlainObject(parsed.settings) ? parsed.settings : undefined);
      if (isPlainObject(parsed.records)) {
        for (const [key, value] of Object.entries(parsed.records)) {
          const record = parseRecord(value);
          if (record) records.set(key, record);
        }
      }
    } catch {
      settings = { ...DEFAULT_SETTINGS };
      records = new Map();
    }
  }

  function save(): void {
    try {
      const now = clock();
      for (const [key, record] of records) if (effectiveRecord(record, now) === EMPTY) records.delete(key);
      storage?.setItem(STORAGE_KEY, JSON.stringify({ version: 1, settings, records: Object.fromEntries(records) }));
    } catch {
      // Storage full or unavailable: keep working in memory.
    }
  }

  function store(key: string, record: DirectionRecord): void {
    if (record.streak === 0 && record.hiddenUntil === null) records.delete(key);
    else records.set(key, record);
    save();
  }

  const current = (chapter: number, word: Word, direction: CardDirection, now: number = clock()) =>
    effectiveRecord(records.get(recordKey(chapter, word, direction)), now);

  /** Directions of a word that will be asked for this choice. */
  function askable(chapter: number, word: Word, choice: Direction, includeHidden: boolean, now: number): CardDirection[] {
    const directions = directionsFor(choice);
    return includeHidden ? directions : directions.filter((d) => !isHidden(chapter, word, d, now));
  }

  function isHidden(chapter: number, word: Word, direction: CardDirection, now: number = clock()): boolean {
    return current(chapter, word, direction, now).hiddenUntil !== null;
  }

  function buildDeck(chapters: Chapter[], direction: Direction, includeHidden: boolean): DeckCard[] {
    const now = clock();
    return chapters.flatMap((chapter) =>
      chapter.words.flatMap((word) => {
        const directions = askable(chapter.number, word, direction, includeHidden, now);
        return directions.length ? [{ chapter: chapter.number, word, directions }] : [];
      }),
    );
  }

  load();

  return {
    settings: (): ProgressSettings => ({ ...settings }),

    /** Applies from now on only; existing hide-until dates are not recomputed. */
    updateSettings(change: Partial<ProgressSettings>): ProgressSettings {
      const next = { ...settings };
      for (const key of ['masterCount', 'hideWeeks'] as const) {
        const value = change[key];
        if (typeof value === 'number' && Number.isFinite(value)) next[key] = value;
      }
      settings = clampSettings(next);
      save();
      return { ...settings };
    },

    streak: (chapter: number, word: Word, direction: CardDirection): number => current(chapter, word, direction).streak,
    hiddenUntil: (chapter: number, word: Word, direction: CardDirection): number | null =>
      current(chapter, word, direction).hiddenUntil,
    isHidden,

    /** Speak answers: a correct answer. */
    recordCorrect(chapter: number, word: Word, direction: CardDirection): void {
      const key = recordKey(chapter, word, direction);
      store(key, applyCorrect(records.get(key), settings, clock()));
    },

    /** Speak answers: a wrong answer (which reveals the answer). Also un-hides. */
    recordMiss(chapter: number, word: Word, direction: CardDirection): void {
      store(recordKey(chapter, word, direction), applyMiss());
    },

    /** Flip cards / Auto listen: hide this word in this direction now (never shortening an existing hide). */
    knowIt(chapter: number, word: Word, direction: CardDirection): void {
      const key = recordKey(chapter, word, direction);
      store(key, applyKnowIt(records.get(key), settings, clock()));
    },

    /** Clears streaks and hidden dates for a chapter, in both directions. */
    resetChapter(chapterNumber: number): void {
      const prefix = chapterPrefix(chapterNumber);
      for (const key of [...records.keys()]) if (key.startsWith(prefix)) records.delete(key);
      save();
    },

    /**
     * Words in the chapter left out of a deck (for "42 words · 12 hidden"): hidden
     * in the chosen direction, or in both directions under "Both".
     */
    hiddenCount(chapter: Chapter, direction: Direction): number {
      const now = clock();
      return chapter.words.filter((word) =>
        directionsFor(direction).every((d) => isHidden(chapter.number, word, d, now)),
      ).length;
    },

    /** Cards of the selected chapters that will be asked. */
    buildDeck,

    cardCount: (chapters: Chapter[], direction: Direction, includeHidden: boolean): number =>
      buildDeck(chapters, direction, includeHidden).length,

    /**
     * Earliest date at which any direction of any selected word comes back
     * (the earliest hide-until among the chosen direction(s)), or null when none are hidden. Used for "All these words are
     * hidden until <date>".
     */
    earliestHiddenUntil(chapters: Chapter[], direction: Direction): number | null {
      const now = clock();
      let earliest: number | null = null;
      for (const chapter of chapters) {
        for (const word of chapter.words) {
          for (const d of directionsFor(direction)) {
            const until = current(chapter.number, word, d, now).hiddenUntil;
            if (until !== null && (earliest === null || until < earliest)) earliest = until;
          }
        }
      }
      return earliest;
    },
  };
}

export type Progress = ReturnType<typeof createProgress>;
