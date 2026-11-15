/**
 * What the voice should say for a card's text: parentheticals such as "(m.)", "(formal)" or "(sentarse)" are
 * notes for the reader (and optional when answering), so they are left out. If nothing would be left, the
 * text is spoken as written.
 */
export function spokenText(text: string): string {
  const spoken = text.replace(/\s*\([^)]*\)/g, '').replace(/\s{2,}/g, ' ').trim();
  return spoken || text;
}
