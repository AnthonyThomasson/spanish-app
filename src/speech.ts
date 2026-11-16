import { Capacitor } from '@capacitor/core';
import { SpeechRecognition as NativeSpeechRecognition } from '@capacitor-community/speech-recognition';
import { QueueStrategy, TextToSpeech } from '@capacitor-community/text-to-speech';
import { ownAudio } from './own-audio';
import { classifyNativeRecognitionError } from './recognition-errors';
import { spokenText } from './spoken-text';
import type { WordKind } from './types';
import { chooseVoice, RecognitionLanguages, speechLanguage, type Language } from './voices';

export interface SpeechRecognitionAlternativeLike {
  transcript: string;
}

export interface SpeechRecognitionResultLike {
  [index: number]: SpeechRecognitionAlternativeLike;
  length: number;
}

export interface SpeechRecognitionEventLike extends Event {
  results: {
    [index: number]: SpeechRecognitionResultLike;
    length: number;
  };
}

export interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}

export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

type RecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

const recognitionLanguages = new RecognitionLanguages();

/** The language tag to listen with: Argentine Spanish where the recognizer supports it. */
export function recognitionLang(language: Language): string {
  return recognitionLanguages.languageFor(language);
}

/**
 * Switches Spanish recognition to es-ES after a recognizer refuses es-AR. False for any other language or when
 * it already switched, so only a Spanish recognizer can trigger it and it cannot loop.
 */
export function fallBackFromArgentineRecognition(language: Language): boolean {
  return recognitionLanguages.unsupported(language);
}

const DEVICE_LANGUAGES_TIMEOUT_MS = 1500;
let deviceLanguages: Promise<void> | null = null;

/**
 * Asks the Android recognizer once which languages it offers (the plugin cannot report an unsupported language
 * when listening: it only says "Didn't understand", which would loop silently). Unavailable on Android 13+, so
 * a missing, failed or slow answer just keeps the default.
 */
function loadDeviceLanguages(): Promise<void> {
  if (deviceLanguages) return deviceLanguages;
  // A late answer still applies to later listens; only this wait is capped.
  const request = NativeSpeechRecognition.getSupportedLanguages()
    .then(({ languages }) => recognitionLanguages.setDeviceLanguages(languages))
    .catch(() => undefined); // keep the default
  let timer: number | undefined;
  const timeout = new Promise<void>((resolve) => { timer = window.setTimeout(resolve, DEVICE_LANGUAGES_TIMEOUT_MS); });
  deviceLanguages = Promise.race([request, timeout]).finally(() => window.clearTimeout(timer));
  return deviceLanguages;
}

export function usingNativeSpeech(): boolean {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';
}

class AndroidSpeechRecognition implements SpeechRecognitionLike {
  lang = 'en-US';
  continuous = false;
  interimResults = false;
  maxAlternatives = 5;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null = null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null = null;
  onend: (() => void) | null = null;
  private aborted = false;
  private ended = false;

  start(): void {
    void this.begin();
  }

  stop(): void {
    this.abort();
  }

  abort(): void {
    if (this.aborted) return;
    this.aborted = true;
    void NativeSpeechRecognition.stop().finally(() => this.finish());
  }

  private async begin(): Promise<void> {
    try {
      const { available } = await NativeSpeechRecognition.available();
      if (!available) {
        this.fail('service-not-allowed');
        return;
      }
      const permission = await NativeSpeechRecognition.requestPermissions();
      if (permission.speechRecognition !== 'granted') {
        this.fail('not-allowed');
        return;
      }
      const spanish = this.lang.toLowerCase().startsWith('es');
      if (spanish) await loadDeviceLanguages();
      if (this.aborted) return;
      const { matches = [] } = await NativeSpeechRecognition.start({
        language: spanish ? recognitionLang('es') : this.lang,
        maxResults: this.maxAlternatives,
        partialResults: false,
        popup: false,
      });
      if (this.aborted) return;
      if (!matches.length) {
        this.fail('no-speech');
        return;
      }
      const results = matches.map((transcript) => ({ 0: { transcript }, length: 1 }));
      this.onresult?.({ results } as unknown as SpeechRecognitionEventLike);
    } catch (error) {
      if (!this.aborted) {
        const message = error instanceof Error ? error.message : String((error as { message?: unknown })?.message ?? error);
        this.fail(classifyNativeRecognitionError(message));
      }
    } finally {
      this.finish();
    }
  }

  private fail(error: string): void {
    if (this.aborted) return;
    this.onerror?.({ error } as SpeechRecognitionErrorEventLike);
  }

  private finish(): void {
    if (this.ended) return;
    this.ended = true;
    this.onend?.();
  }
}

export function recognitionConstructor(): RecognitionConstructor | undefined {
  if (usingNativeSpeech()) return AndroidSpeechRecognition;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

interface NativeUtterance {
  text: string;
  language: Language;
  resolve: () => void;
}

export class Speaker {
  private voices: SpeechSynthesisVoice[] = [];
  private nativeUtterance: NativeUtterance | null = null;
  private nativePaused = false;

  constructor() {
    if (usingNativeSpeech() || !('speechSynthesis' in window)) return;
    this.refreshVoices();
    window.speechSynthesis.addEventListener('voiceschanged', () => this.refreshVoices());
  }

  private refreshVoices(): void {
    this.voices = window.speechSynthesis.getVoices();
  }

  speak(text: string, language: Language, kind: WordKind = 'word'): Promise<void> {
    const end = ownAudio.begin(); // the TTS engine takes audio focus; see own-audio.ts
    return this.play(spokenText(text, kind), language).finally(end);
  }

  private play(text: string, language: Language): Promise<void> {
    if (usingNativeSpeech()) return this.speakNative(text, language);
    if (!('speechSynthesis' in window)) return Promise.resolve();
    this.refreshVoices();
    window.speechSynthesis.cancel();

    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      const voice = this.voiceFor(language);
      utterance.lang = speechLanguage(language, voice);
      utterance.rate = language === 'es' ? 0.88 : 0.95;
      utterance.voice = voice;
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  }

  private speakNative(text: string, language: Language): Promise<void> {
    this.nativeUtterance?.resolve();
    return new Promise((resolve) => {
      const utterance = { text, language, resolve };
      this.nativeUtterance = utterance;
      void this.playNative(utterance);
    });
  }

  private async playNative(utterance: NativeUtterance): Promise<void> {
    if (this.nativePaused || this.nativeUtterance !== utterance) return;
    try {
      const { voices } = await TextToSpeech.getSupportedVoices();
      this.voices = voices;
      const voice = this.voiceFor(utterance.language);
      const voiceIndex = voice ? voices.indexOf(voice) : -1;
      if (this.nativePaused || this.nativeUtterance !== utterance) return;
      await TextToSpeech.speak({
        text: utterance.text,
        lang: speechLanguage(utterance.language, voice),
        rate: utterance.language === 'es' ? 0.88 : 0.95,
        ...(voiceIndex >= 0 ? { voice: voiceIndex } : {}),
        queueStrategy: QueueStrategy.Flush,
      });
    } catch {
    } finally {
      if (this.nativeUtterance === utterance && !this.nativePaused) {
        this.nativeUtterance = null;
        utterance.resolve();
      }
    }
  }

  private voiceFor(language: Language): SpeechSynthesisVoice | null {
    return chooseVoice(this.voices, language);
  }

  pause(): void {
    if (usingNativeSpeech()) {
      this.nativePaused = true;
      void TextToSpeech.stop();
    } else if ('speechSynthesis' in window) {
      window.speechSynthesis.pause();
    }
  }

  resume(): void {
    if (usingNativeSpeech()) {
      this.nativePaused = false;
      if (this.nativeUtterance) void this.playNative(this.nativeUtterance);
    } else if ('speechSynthesis' in window) {
      window.speechSynthesis.resume();
    }
  }

  cancel(): void {
    if (usingNativeSpeech()) {
      const utterance = this.nativeUtterance;
      this.nativeUtterance = null;
      this.nativePaused = false;
      utterance?.resolve();
      void TextToSpeech.stop();
    } else if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}
