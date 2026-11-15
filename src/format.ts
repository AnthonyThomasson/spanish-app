/** Display text for deck setup. Pure, so it can be unit tested. */

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`;
}

/** "42 words · 12 hidden", or just "42 words" when none are hidden. */
export function formatChapterCount(total: number, hidden: number): string {
  const words = pluralize(total, 'word');
  return hidden > 0 ? `${words} · ${hidden.toLocaleString()} hidden` : words;
}

/** "3 chapters · 120 cards", where `cards` only counts cards that will be asked. */
export function formatSelectionSummary(chapterCount: number, cardCount: number): string {
  return `${pluralize(chapterCount, 'chapter')} · ${pluralize(cardCount, 'card')}`;
}

/** A readable date in the viewer's time zone, e.g. "December 6, 2026". */
export function formatHiddenDate(epochMs: number, locale?: string): string {
  return new Date(epochMs).toLocaleDateString(locale, { year: 'numeric', month: 'long', day: 'numeric' });
}

export function allHiddenMessage(earliestEpochMs: number, locale?: string): string {
  return `All these words are hidden until ${formatHiddenDate(earliestEpochMs, locale)}.`;
}
