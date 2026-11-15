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

export type CardDirection = 'es-en' | 'en-es';
export type Direction = CardDirection | 'both';

/** A card in the running deck: the word, its chapter, and the direction it is asked in. */
export interface Card {
  chapter: number;
  word: Word;
  direction: CardDirection;
}
export type Mode = 'flip' | 'auto' | 'answer';
