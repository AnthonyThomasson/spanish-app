export interface Word {
  spanish: string;
  english: string;
  partOfSpeech?: string;
  gender?: string;
  sourcePage: number;
}

export interface Chapter {
  number: number;
  title: string;
  words: Word[];
}

export interface Vocabulary {
  source: string;
  chapters: Chapter[];
}

export type Direction = 'es-en' | 'en-es';
export type Mode = 'flip' | 'auto' | 'answer';
