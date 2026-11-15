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
  return voice?.lang.replace('_', '-') ?? (language === 'es' ? 'es-ES' : 'en-US');
}

/** The language tag to listen with. Spanish asks for Argentine unless a recognizer has refused it. */
export function recognitionLanguage(language: Language, argentineUnsupported = false): string {
  if (language === 'en') return 'en-US';
  return argentineUnsupported ? 'es-ES' : 'es-AR';
}

const SPANISH_RECOGNITION_PREFERENCE = ['es-ar', 'es-es', 'es-mx'];

/**
 * The Spanish recognition language to use from the device's list: Argentine, then Spain, then Mexican, then any
 * Spanish. Returns the device's own spelling, or null when the list has no Spanish or is unusable.
 */
export function pickSpanishRecognitionLanguage(supported: unknown): string | null {
  if (!Array.isArray(supported)) return null;
  const tags = supported.filter((tag): tag is string => typeof tag === 'string');
  const normalized = (tag: string) => tag.toLowerCase().replace('_', '-');
  for (const preferred of SPANISH_RECOGNITION_PREFERENCE) {
    const found = tags.find((tag) => normalized(tag) === preferred);
    if (found) return found;
  }
  return tags.find((tag) => normalized(tag).startsWith('es')) ?? null;
}

/** Which language each recognizer listens in, and the one-time fall-back from Argentine Spanish. */
export class RecognitionLanguages {
  private argentineUnsupported = false;
  private deviceSpanish: string | null = null;

  languageFor(language: Language): string {
    if (language === 'es' && this.deviceSpanish) return this.deviceSpanish;
    return recognitionLanguage(language, this.argentineUnsupported);
  }

  /** Records what a native recognizer says it supports. Ignored when it has no Spanish. */
  setDeviceLanguages(supported: unknown): void {
    this.deviceSpanish = pickSpanishRecognitionLanguage(supported);
  }

  /**
   * A recognizer refused its language. True when the Spanish recognizer should be retried in es-ES; false for
   * English or when it already fell back, so an unrelated or repeated error cannot loop.
   */
  unsupported(language: Language): boolean {
    if (language !== 'es' || this.argentineUnsupported) return false;
    this.argentineUnsupported = true;
    return true;
  }
}
