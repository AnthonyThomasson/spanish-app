/**
 * Number words to digits, so a recognizer that hears "2" and a card that says "two" (or "dos") agree.
 * Covers 0 to the millions in English and Spanish (accents already folded).
 */

type Kind = 'zero' | 'unit' | 'teen' | 'tens' | 'tensunit' | 'hundred' | 'hundreds' | 'thousand' | 'million';
interface NumberWord {
  kind: Kind;
  value: number;
}

const words = new Map<string, NumberWord>();
const add = (kind: Kind, entries: Record<string, number>) => {
  for (const [word, value] of Object.entries(entries)) words.set(word, { kind, value });
};

add('zero', { zero: 0, cero: 0 });
add('unit', {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9,
  uno: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
});
add('teen', {
  ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
  diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15, dieciseis: 16, diecisiete: 17, dieciocho: 18, diecinueve: 19,
});
add('tens', {
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
  veinte: 20, treinta: 30, cuarenta: 40, cincuenta: 50, sesenta: 60, setenta: 70, ochenta: 80, noventa: 90,
});
add('tensunit', {
  veintiuno: 21, veintiun: 21, veintiuna: 21, veintidos: 22, veintitres: 23, veinticuatro: 24, veinticinco: 25,
  veintiseis: 26, veintisiete: 27, veintiocho: 28, veintinueve: 29,
});
add('hundred', { hundred: 100, cien: 100, ciento: 100 });
add('hundreds', {
  doscientos: 200, doscientas: 200, trescientos: 300, trescientas: 300, cuatrocientos: 400, cuatrocientas: 400,
  quinientos: 500, quinientas: 500, seiscientos: 600, seiscientas: 600, setecientos: 700, setecientas: 700,
  ochocientos: 800, ochocientas: 800, novecientos: 900, novecientas: 900,
});
add('thousand', { thousand: 1000, mil: 1000 });
add('million', { million: 1_000_000, millon: 1_000_000, millones: 1_000_000 });

const small: Kind[] = ['unit', 'teen', 'tens', 'tensunit'];
/** Which kinds of number word may follow each kind inside one number. */
const followers: Record<Kind, Kind[]> = {
  zero: [],
  unit: ['hundred', 'thousand', 'million'],
  teen: ['thousand', 'million'],
  tens: ['unit', 'thousand', 'million'],
  tensunit: ['thousand', 'million'],
  hundred: [...small, 'thousand', 'million'],
  hundreds: [...small, 'thousand', 'million'],
  thousand: [...small, 'hundred', 'hundreds', 'million'],
  million: [...small, 'hundred', 'hundreds', 'thousand'],
};

/** Whether "and" (English) or "y" (Spanish) may join `previous` to the number word `next`. */
function connects(connector: string, previous: Kind, next: Kind): boolean {
  if (connector === 'y') return previous === 'tens' && next === 'unit';
  return ['hundred', 'thousand', 'million'].includes(previous) && [...small].includes(next);
}

function readNumber(tokens: string[], start: number): { value: number; end: number } | null {
  let total = 0;
  let current = 0;
  let previous: Kind | null = null;
  let index = start;
  let end = start;
  while (index < tokens.length) {
    let word = words.get(tokens[index]);
    let next = index;
    if (!word && previous && (tokens[index] === 'and' || tokens[index] === 'y')) {
      const after = words.get(tokens[index + 1]);
      if (after && connects(tokens[index], previous, after.kind)) {
        word = after;
        next = index + 1;
      }
    }
    if (!word) break;
    if (previous === null ? false : !followers[previous].includes(word.kind)) break;
    if (word.kind === 'hundred') current = (current || 1) * 100;
    else if (word.kind === 'thousand' || word.kind === 'million') {
      total += (current || 1) * word.value;
      current = 0;
    } else current += word.value;
    previous = word.kind;
    index = next + 1;
    end = index;
  }
  return previous === null ? null : { value: total + current, end };
}

/** Replaces each run of number words with its digits: ["forty", "two", "cats"] becomes ["42", "cats"]. */
export function canonicalizeNumbers(tokens: string[]): string[] {
  const result: string[] = [];
  let index = 0;
  while (index < tokens.length) {
    const number = readNumber(tokens, index);
    if (number) {
      result.push(String(number.value));
      index = number.end;
    } else {
      result.push(tokens[index]);
      index += 1;
    }
  }
  return result;
}

/** The number a whole answer says ("2", "two", "forty-two", "cuarenta y dos"), or null if it is anything else. */
export function numberValue(text: string): number | null {
  const tokens = text
    .toLocaleLowerCase()
    .replace(/(\d),(?=\d{3}\b)/g, '$1')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .split(/\s+/)
    .filter(Boolean);
  const canonical = canonicalizeNumbers(tokens);
  return canonical.length === 1 && /^\d+$/.test(canonical[0]) ? Number(canonical[0]) : null;
}
