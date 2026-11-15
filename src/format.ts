/** Display text for deck setup. Pure, so it can be unit tested. */

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count.toLocaleString()} ${count === 1 ? singular : plural}`;
}

/** "42 cards · 12 hidden", or just "42 cards" when none are hidden. A card is a word, sentence or conjugation. */
export function formatChapterCount(total: number, hidden: number): string {
  const cards = pluralize(total, 'card');
  return hidden > 0 ? `${cards} · ${hidden.toLocaleString()} hidden` : cards;
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
  return `All these cards are hidden until ${formatHiddenDate(earliestEpochMs, locale)}.`;
}
