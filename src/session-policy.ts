import type { Mode } from './types';

export interface VisibilityState {
  hidden: boolean;
  active: boolean;
  mode: Mode;
  paused: boolean;
  /** True on native Android, where a foreground service keeps the session running. */
  native: boolean;
}

/** Browsers can't keep audio running in a hidden tab, so they pause; native Android keeps going. */
export function shouldAutoPauseWhenHidden(state: VisibilityState): boolean {
  return state.hidden && state.active && !state.native && state.mode !== 'flip' && !state.paused;
}
