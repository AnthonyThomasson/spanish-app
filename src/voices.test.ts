import { describe, expect, it } from 'vitest';
import { chooseVoice, pickSpanishRecognitionLanguage, RecognitionLanguages, recognitionLanguage, speechLanguage } from './voices';

const voice = (lang: string, name = lang) => ({ lang, name });

describe('chooseVoice', () => {
  it('prefers an Argentine Spanish voice over Mexican and Spain', () => {
    const voices = [voice('es-ES'), voice('es-MX'), voice('es-AR'), voice('en-US')];
    expect(chooseVoice(voices, 'es')?.lang).toBe('es-AR');
  });

  it('falls back to Mexican, then Spain, then any Spanish voice', () => {
    expect(chooseVoice([voice('es-ES'), voice('es-MX')], 'es')?.lang).toBe('es-MX');
    expect(chooseVoice([voice('es-CO'), voice('es-ES')], 'es')?.lang).toBe('es-ES');
    expect(chooseVoice([voice('en-US'), voice('es-CO')], 'es')?.lang).toBe('es-CO');
  });

  it('reads Android-style underscore and mixed-case language tags', () => {
    expect(chooseVoice([voice('es_ES'), voice('es_AR')], 'es')?.lang).toBe('es_AR');
    expect(chooseVoice([voice('ES-ar')], 'es')?.lang).toBe('ES-ar');
  });

  it('returns null when there is no Spanish voice', () => {
    expect(chooseVoice([voice('en-US')], 'es')).toBeNull();
    expect(chooseVoice([], 'es')).toBeNull();
  });

  it('prefers US English for English and is unaffected by es-AR', () => {
    expect(chooseVoice([voice('en-GB'), voice('en-US'), voice('es-AR')], 'en')?.lang).toBe('en-US');
    expect(chooseVoice([voice('en-GB'), voice('es-AR')], 'en')?.lang).toBe('en-GB');
  });
});

describe('speechLanguage', () => {
  it('uses the chosen voice language when there is one', () => {
    expect(speechLanguage('es', voice('es-AR'))).toBe('es-AR');
  });

  it('writes an Android underscore tag as a BCP 47 tag', () => {
    expect(speechLanguage('es', voice('es_AR'))).toBe('es-AR');
  });

  it('falls back to es-ES and en-US without a voice', () => {
    expect(speechLanguage('es', null)).toBe('es-ES');
    expect(speechLanguage('en', null)).toBe('en-US');
  });

  it('keeps English as en-US even if a voice is English-GB-only', () => {
    expect(speechLanguage('en', voice('en-GB'))).toBe('en-GB');
  });
});

describe('recognitionLanguage', () => {
  it('asks for Argentine Spanish and US English', () => {
    expect(recognitionLanguage('es')).toBe('es-AR');
    expect(recognitionLanguage('en')).toBe('en-US');
  });

  it('falls back to Spain Spanish once told Argentine is unsupported, and stays there', () => {
    const fallback = recognitionLanguage('es', true);
    expect(fallback).toBe('es-ES');
    expect(recognitionLanguage('en', true)).toBe('en-US');
  });
});

describe('pickSpanishRecognitionLanguage', () => {
  it('prefers Argentine, then Spain, then Mexican, then any Spanish', () => {
    expect(pickSpanishRecognitionLanguage(['en-US', 'es-ES', 'es-MX', 'es-AR'])).toBe('es-AR');
    expect(pickSpanishRecognitionLanguage(['en-US', 'es-MX', 'es-ES'])).toBe('es-ES');
    expect(pickSpanishRecognitionLanguage(['en-US', 'es-MX'])).toBe('es-MX');
    expect(pickSpanishRecognitionLanguage(['en-US', 'es-CO'])).toBe('es-CO');
  });

  it('returns the device\'s own spelling of the tag', () => {
    expect(pickSpanishRecognitionLanguage(['en_US', 'es_AR'])).toBe('es_AR');
    expect(pickSpanishRecognitionLanguage(['ES-ar'])).toBe('ES-ar');
  });

  it('is null when no Spanish is offered or the list is unusable', () => {
    expect(pickSpanishRecognitionLanguage(['en-US', 'fr-FR'])).toBeNull();
    expect(pickSpanishRecognitionLanguage([])).toBeNull();
    expect(pickSpanishRecognitionLanguage(undefined)).toBeNull();
    expect(pickSpanishRecognitionLanguage([42, null, 'es-AR'])).toBe('es-AR');
  });
});

describe('RecognitionLanguages', () => {
  it('asks for Argentine Spanish and US English by default', () => {
    const languages = new RecognitionLanguages();
    expect(languages.languageFor('es')).toBe('es-AR');
    expect(languages.languageFor('en')).toBe('en-US');
  });

  it('falls back to es-ES once, and only for Spanish', () => {
    const languages = new RecognitionLanguages();
    expect(languages.unsupported('en')).toBe(false);
    expect(languages.languageFor('es')).toBe('es-AR');
    expect(languages.unsupported('es')).toBe(true);
    expect(languages.languageFor('es')).toBe('es-ES');
    expect(languages.languageFor('en')).toBe('en-US');
    expect(languages.unsupported('es')).toBe(false); // already fallen back: do not loop
  });

  it('uses the language the device reports once it is known', () => {
    const languages = new RecognitionLanguages();
    languages.setDeviceLanguages(['en-US', 'es-MX']);
    expect(languages.languageFor('es')).toBe('es-MX');
    expect(languages.languageFor('en')).toBe('en-US');
  });

  it('still falls back to es-ES when the device listed es-AR but the recognizer refuses it', () => {
    const languages = new RecognitionLanguages();
    languages.setDeviceLanguages(['es-AR', 'es-ES']);
    expect(languages.languageFor('es')).toBe('es-AR');
    expect(languages.unsupported('es')).toBe(true);
    expect(languages.languageFor('es')).toBe('es-ES');
  });

  it('keeps the default when the device list has no Spanish or is unavailable', () => {
    const languages = new RecognitionLanguages();
    languages.setDeviceLanguages(['en-US']);
    expect(languages.languageFor('es')).toBe('es-AR');
    languages.setDeviceLanguages(undefined);
    expect(languages.languageFor('es')).toBe('es-AR');
  });
});
