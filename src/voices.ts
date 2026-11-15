export type Language = 'es' | 'en';

interface HasLang {
  lang: string;
}

/** Spanish voices in order of preference: Argentine first, then the existing Mexican and Spain fallbacks. */
const SPANISH_PREFERENCE = ['es-ar', 'es-mx', 'es-es'];

const tag = (voice: HasLang) => voice.lang.toLowerCase().replace('_', '-');

/** The best installed voice for a language, or null when none matches. Accepts "es-AR" and "es_AR" tags. */
export function chooseVoice<T extends HasLang>(voices: T[], language: Language): T | null {
  const matching = voices.filter((voice) => tag(voice).startsWith(language));
  if (language === 'es') {
    for (const preferred of SPANISH_PREFERENCE) {
      const found = matching.find((voice) => tag(voice).startsWith(preferred));
      if (found) return found;
    }
    return matching[0] ?? null;
  }
  return matching.find((voice) => tag(voice).startsWith('en-us')) ?? matching[0] ?? null;
}

/** The language tag to speak with: the chosen voice's own, else a safe default. */
export function speechLanguage(language: Language, voice: HasLang | null): string {
  return voice?.lang ?? (language === 'es' ? 'es-ES' : 'en-US');
}

/** The language tag to listen with. Spanish asks for Argentine unless a recognizer has refused it. */
export function recognitionLanguage(language: Language, argentineUnsupported = false): string {
  if (language === 'en') return 'en-US';
  return argentineUnsupported ? 'es-ES' : 'es-AR';
}
