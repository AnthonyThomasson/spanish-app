import type { Mode } from './types';

export type BackgroundMode = Exclude<Mode, 'flip'>;

export interface NotificationInput {
  mode: BackgroundMode;
  /** Zero-based index of the current card. */
  index: number;
  total: number;
  prompt: string;
  answer: string;
  revealed: boolean;
  paused: boolean;
  /** Why the session paused itself (for example a microphone failure); replaces the card text while paused. */
  notice?: string | null;
}

export interface NotificationState {
  title: string;
  text: string;
  paused: boolean;
  mode: BackgroundMode;
}

const MODE_LABELS: Record<BackgroundMode, string> = { auto: 'Auto listen', answer: 'Speak answers' };

export function buildNotification(input: NotificationInput): NotificationState {
  return {
    title: `${MODE_LABELS[input.mode]} · ${input.index + 1} / ${input.total}`,
    text: input.paused && input.notice ? input.notice : input.revealed ? `${input.prompt} → ${input.answer}` : input.prompt,
    paused: input.paused,
    mode: input.mode,
  };
}
