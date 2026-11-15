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

export function isCorrectAnswer(spoken: string, expected: string): boolean {
  const actual = normalizeAnswer(spoken);
  if (!actual) return false;
  return answerAlternatives(expected).some((alternative) => alternative === actual);
}

/** Whether recognition returned anything to judge: blank or whitespace-only results are silence, not a wrong answer. */
export function hasSpokenText(transcripts: string[]): boolean {
  return transcripts.some((transcript) => transcript.trim() !== '');
}
