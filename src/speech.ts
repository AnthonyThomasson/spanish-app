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

export function recognitionConstructor(): RecognitionConstructor | undefined {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export class Speaker {
  private voices: SpeechSynthesisVoice[] = [];

  constructor() {
    if (!('speechSynthesis' in window)) return;
    this.refreshVoices();
    window.speechSynthesis.addEventListener('voiceschanged', () => this.refreshVoices());
  }

  private refreshVoices(): void {
    this.voices = window.speechSynthesis.getVoices();
  }

  speak(text: string, language: 'es' | 'en'): Promise<void> {
    if (!('speechSynthesis' in window)) return Promise.resolve();
    this.refreshVoices();
    window.speechSynthesis.cancel();

    return new Promise((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = language === 'es' ? 'es-ES' : 'en-US';
      utterance.rate = language === 'es' ? 0.88 : 0.95;
      utterance.voice = this.voiceFor(language);
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  }

  private voiceFor(language: 'es' | 'en'): SpeechSynthesisVoice | null {
    const matching = this.voices.filter((voice) => voice.lang.toLowerCase().startsWith(language));
    if (language === 'es') {
      return matching.find((voice) => voice.lang.toLowerCase().startsWith('es-mx'))
        ?? matching.find((voice) => voice.lang.toLowerCase().startsWith('es-es'))
        ?? matching[0]
        ?? null;
    }
    return matching.find((voice) => voice.lang.toLowerCase().startsWith('en-us'))
      ?? matching[0]
      ?? null;
  }

  pause(): void {
    if ('speechSynthesis' in window) window.speechSynthesis.pause();
  }

  resume(): void {
    if ('speechSynthesis' in window) window.speechSynthesis.resume();
  }

  cancel(): void {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  }
}
