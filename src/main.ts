import './style.css';
import { backgroundSession } from './background-session';
import { allHiddenMessage, formatChapterCount, formatSelectionSummary, pluralize } from './format';
import { isCorrectAnswer } from './matching';
import { buildNotification } from './notification';
import { ensureMicrophonePermission } from './microphone';
import { ownAudio } from './own-audio';
import { createProgress, type DeckCard } from './progress';
import { RecognitionMonitor, recognitionFailureMessage, recognitionFailureNotice, recognitionRetryDelay } from './recognition-errors';
import { dispatchBackgroundAction } from './session-actions';
import { singleFlight } from './single-flight';
import { shouldAutoPauseWhenHidden } from './session-policy';
import { recognitionConstructor, Speaker, usingNativeSpeech, type SpeechRecognitionLike } from './speech';
import type { Card, CardDirection, Chapter, Direction, Mode, Vocabulary } from './types';
import { createWait } from './wait';

const app = document.querySelector<HTMLDivElement>('#app')!;

app.innerHTML = `
  <main class="shell">
    <header class="masthead">
      <a class="brand" href="./" aria-label="Paso home"><span class="brand-mark">P</span><span>paso</span></a>
      <span class="eyebrow">Spanish, one step at a time</span>
    </header>

    <section id="setup" class="setup-view">
      <div class="intro">
        <p class="kicker">YOUR VOCABULARY, OUT LOUD</p>
        <h1>Make the words<br><em>stick.</em></h1>
        <p class="intro-copy">Build a deck from your book, then tap, listen, or speak your way through it.</p>
      </div>

      <div id="loading" class="notice">Loading your vocabulary…</div>
      <form id="deck-form" class="deck-builder" hidden>
        <section class="panel chapters-panel">
          <div class="section-heading">
            <div><span class="step-number">01</span><h2>Choose chapters</h2></div>
            <div class="text-actions"><button type="button" id="select-all">All</button><button type="button" id="select-none">None</button></div>
          </div>
          <div id="chapter-list" class="chapter-list"></div>
          <p id="selection-summary" class="selection-summary" aria-live="polite"></p>
        </section>

        <section class="panel settings-panel">
          <div class="section-heading"><div><span class="step-number">02</span><h2>Set your pace</h2></div></div>
          <fieldset>
            <legend>Direction</legend>
            <div class="segmented three-up">
              <label><input type="radio" name="direction" value="es-en"><span><b>Spanish</b><small>to English</small></span></label>
              <label><input type="radio" name="direction" value="en-es"><span><b>English</b><small>to Spanish</small></span></label>
              <label><input type="radio" name="direction" value="both" checked><span><b>Both</b><small>mixed</small></span></label>
            </div>
          </fieldset>
          <fieldset>
            <legend>Practice mode</legend>
            <div class="mode-options">
              <label><input type="radio" name="mode" value="flip" checked><span class="mode-copy"><b>Flip cards</b><small>Tap to reveal, at your own pace</small></span><span class="radio-dot"></span></label>
              <label><input type="radio" name="mode" value="auto"><span class="mode-copy"><b>Auto listen</b><small>Hands-free prompts and answers</small></span><span class="radio-dot"></span></label>
              <label><input type="radio" name="mode" value="answer"><span class="mode-copy"><b>Speak answers</b><small>Respond aloud to move forward</small></span><span class="radio-dot"></span></label>
            </div>
          </fieldset>
          <div id="recognition-note" class="support-note" hidden></div>
          <div id="delay-setting" class="range-setting" hidden>
            <label for="delay">Thinking time <output id="delay-value" for="delay">3 seconds</output></label>
            <input id="delay" type="range" min="1" max="8" step="0.5" value="3">
            <div class="range-labels"><span>1 sec</span><span>8 sec</span></div>
          </div>
          <div class="range-setting">
            <label for="master-count">Correct answers to master <output id="master-count-value" for="master-count"></output></label>
            <input id="master-count" type="range" min="1" max="10" step="1" value="3">
            <div class="range-labels"><span>1</span><span>10</span></div>
          </div>
          <div class="range-setting">
            <label for="hide-weeks">Hide mastered words for <output id="hide-weeks-value" for="hide-weeks"></output></label>
            <input id="hide-weeks" type="range" min="1" max="12" step="1" value="3">
            <div class="range-labels"><span>1 week</span><span>12 weeks</span></div>
          </div>
          <label class="shuffle-toggle"><span><b>Shuffle deck</b><small>Mix up the card order</small></span><input id="shuffle" type="checkbox" checked><span class="switch" aria-hidden="true"></span></label>
          <label class="shuffle-toggle"><span><b>Include hidden words</b><small>Review words you’ve already mastered</small></span><input id="include-hidden" type="checkbox"><span class="switch" aria-hidden="true"></span></label>
          <p id="start-error" class="form-error" role="alert"></p>
          <div id="all-hidden" class="hidden-notice" role="status" hidden>
            <p id="all-hidden-message"></p>
            <button id="include-and-start" class="secondary" type="button">Include hidden words and start</button>
          </div>
          <button class="primary start-button" type="submit">Start practicing <span aria-hidden="true">→</span></button>
        </section>
      </form>
    </section>

    <section id="session" class="session-view" hidden>
      <div class="session-topbar">
        <button id="end-session" class="text-button" type="button"><span aria-hidden="true">←</span> Deck setup</button>
        <div class="session-label"><span id="session-mode"></span><span class="dot-separator">·</span><span id="session-direction"></span></div>
        <span id="progress-text" class="progress-text"></span>
      </div>
      <div class="progress-track" aria-hidden="true"><div id="progress-bar"></div></div>

      <div class="practice-area">
        <p id="prompt-label" class="prompt-label"></p>
        <button id="flashcard" class="flashcard" type="button" aria-label="Reveal answer">
          <span id="card-prompt" class="card-prompt"></span>
          <span id="card-answer" class="card-answer" hidden></span>
          <span id="card-detail" class="card-detail" hidden></span>
          <span id="flip-hint" class="flip-hint">Tap to reveal</span>
        </button>
        <div class="speech-status" aria-live="polite">
          <span id="status-indicator" class="status-indicator"></span>
          <p id="session-status">Take your time.</p>
        </div>
        <p id="heard-text" class="heard-text"></p>
        <div class="session-controls">
          <button id="pause-button" class="secondary" type="button" hidden>Pause</button>
          <button id="know-button" class="secondary" type="button" hidden>Know it</button>
          <button id="next-button" class="primary" type="button">Next card <span aria-hidden="true">→</span></button>
        </div>
      </div>
    </section>

    <section id="complete" class="complete-view" hidden>
      <span class="completion-mark" aria-hidden="true">✓</span>
      <p class="kicker">DECK COMPLETE</p>
      <h1>That’s another<br><em>step forward.</em></h1>
      <p id="complete-summary"></p>
      <div class="completion-actions"><button id="restart-deck" class="primary" type="button">Practice again</button><button id="new-deck" class="secondary" type="button">Choose another deck</button></div>
    </section>

    <footer><span>From <i>Complete Spanish Step-by-Step</i></span><span>Local data. Private practice.</span></footer>
  </main>
`;

function element<T extends HTMLElement>(id: string): T {
  return document.getElementById(id) as T;
}

const setupView = element<HTMLElement>('setup');
const sessionView = element<HTMLElement>('session');
const completeView = element<HTMLElement>('complete');
const form = element<HTMLFormElement>('deck-form');
const chapterList = element<HTMLDivElement>('chapter-list');
const speaker = new Speaker();
const recognitionMonitor = new RecognitionMonitor();

let chapters: Chapter[] = [];
const progress = createProgress();
const chapterCountLabels = new Map<number, HTMLElement>();
/** Taps on "Know it" this soon after a card appears are ignored, so a double tap can't hide the next card unseen. */
const KNOW_IT_GUARD_MS = 400;

let deck: Card[] = [];
let cardShownAt = 0;
let currentIndex = 0;
let revealed = false;
let paused = false;
let active = false;
let runId = 0;
let recognition: SpeechRecognitionLike | null = null;
/** Why the session paused itself after a recognition failure; shown in the notification until Resume or the next card. */
let failureNotice: string | null = null;
let settings = { direction: 'both' as Direction, mode: 'flip' as Mode, delay: 3, shuffle: true, includeHidden: false };

const promptFor = ({ word, direction }: Card) => direction === 'es-en' ? word.spanish : word.english;
const answerFor = ({ word, direction }: Card) => direction === 'es-en' ? word.english : word.spanish;
const promptLanguage = ({ direction }: Card) => direction === 'es-en' ? 'es' as const : 'en' as const;
const answerLanguage = ({ direction }: Card) => direction === 'es-en' ? 'en' as const : 'es' as const;

/** The direction a card is asked in: picked at random from its allowed (non-hidden, unless hidden words are included) directions. */
const pickDirection = (card: DeckCard): CardDirection => card.directions[Math.floor(Math.random() * card.directions.length)];

async function loadVocabulary(): Promise<void> {
  try {
    const response = await fetch('/data/vocab.json');
    if (!response.ok) throw new Error('missing');
    const data = await response.json() as Vocabulary;
    chapters = data.chapters.filter((chapter) => chapter.words.length > 0);
    if (!chapters.length) throw new Error('empty');
    renderChapters();
    element('loading').hidden = true;
    form.hidden = false;
    updateSupportNote();
  } catch {
    element('loading').className = 'notice error-notice';
    element('loading').textContent = 'Vocabulary data is missing. Generate it locally with: uv run scripts/extract_vocab.py "/path/to/Complete Spanish Step-by-Step.pdf"';
  }
}

function renderChapters(): void {
  chapterCountLabels.clear();
  chapters.forEach((chapter, index) => {
    // The row wrapper holds the selectable <label> and, outside it, the reset actions.
    const item = document.createElement('div');
    item.className = 'chapter-item';
    const label = document.createElement('label');
    label.className = 'chapter-option';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = String(chapter.number);
    checkbox.checked = index === 0;
    checkbox.addEventListener('change', refreshSetup);
    const number = document.createElement('span');
    number.className = 'chapter-number';
    number.textContent = String(chapter.number).padStart(2, '0');
    const title = document.createElement('span');
    title.className = 'chapter-title';
    title.textContent = chapter.title;
    const count = document.createElement('span');
    count.className = 'chapter-count';
    chapterCountLabels.set(chapter.number, count);
    label.append(checkbox, number, title, count);
    item.append(label, chapterActions(chapter));
    chapterList.append(item);
  });
  refreshSetup();
}

/** "Reset progress" with an inline Reset / Keep confirmation. Sits beside the chapter <label>, not inside it. */
function chapterActions(chapter: Chapter): HTMLElement {
  const actions = document.createElement('div');
  actions.className = 'chapter-actions';
  const button = (text: string, className: string, label: string | null, onClick: () => void) => {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = className;
    el.textContent = text;
    if (label) el.setAttribute('aria-label', label);
    el.addEventListener('click', onClick);
    return el;
  };
  const confirm = document.createElement('span');
  confirm.className = 'chapter-confirm';
  confirm.hidden = true;
  const ask = button('Reset progress', 'chapter-action', `Reset progress for chapter ${chapter.number}`, () => {
    confirm.hidden = false;
    ask.hidden = true;
    yes.focus();
  });
  const close = () => {
    confirm.hidden = true;
    ask.hidden = false;
    ask.focus();
  };
  const yes = button('Reset', 'chapter-action danger', `Confirm reset of chapter ${chapter.number}`, () => {
    progress.resetChapter(chapter.number);
    close();
    refreshSetup();
  });
  const no = button('Keep', 'chapter-action', 'Keep progress', close);
  const question = document.createElement('span');
  question.textContent = 'Clear streaks and hidden words?';
  confirm.append(question, yes, no);
  actions.append(ask, confirm);
  return actions;
}

function selectedChapterNumbers(): number[] {
  return Array.from(chapterList.querySelectorAll<HTMLInputElement>('input:checked')).map((input) => Number(input.value));
}

const chosenDirection = () => (form.elements.namedItem('direction') as RadioNodeList).value as Direction;
const includeHiddenChecked = () => element<HTMLInputElement>('include-hidden').checked;
const selectedChapters = () => {
  const selected = selectedChapterNumbers();
  return chapters.filter((chapter) => selected.includes(chapter.number));
};

/** Re-derives everything in deck setup that depends on progress, direction, selection or the toggle. */
function refreshSetup(): void {
  const direction = chosenDirection();
  for (const chapter of chapters) {
    chapterCountLabels.get(chapter.number)!.textContent = formatChapterCount(chapter.words.length, progress.hiddenCount(chapter, direction));
  }
  const selected = selectedChapters();
  element('selection-summary').textContent = formatSelectionSummary(selected.length, progress.cardCount(selected, direction, includeHiddenChecked()));
  element('all-hidden').hidden = true;
}

function updateMasterySettings(): void {
  const { masterCount, hideWeeks } = progress.settings();
  element<HTMLInputElement>('master-count').value = String(masterCount);
  element<HTMLInputElement>('hide-weeks').value = String(hideWeeks);
  element('master-count-value').textContent = pluralize(masterCount, 'correct answer');
  element('hide-weeks-value').textContent = pluralize(hideWeeks, 'week');
}

function updateSupportNote(): void {
  const answerSelected = form.elements.namedItem('mode') instanceof RadioNodeList
    && (form.elements.namedItem('mode') as RadioNodeList).value === 'answer';
  const note = element('recognition-note');
  note.hidden = !answerSelected;
  if (answerSelected) {
    note.textContent = usingNativeSpeech()
      ? 'Native Android speech recognition is enabled. You’ll be asked for microphone access when a card begins.'
      : recognitionConstructor()
        ? 'Your browser supports speech recognition. You’ll be asked for microphone access when a card begins.'
        : 'Speech recognition isn’t supported in this browser. Use Chrome or Safari for Speak answers mode, or choose another mode.';
  }
}

function readSettings(): void {
  settings = {
    direction: (form.elements.namedItem('direction') as RadioNodeList).value as Direction,
    mode: (form.elements.namedItem('mode') as RadioNodeList).value as Mode,
    delay: Number(element<HTMLInputElement>('delay').value),
    shuffle: element<HTMLInputElement>('shuffle').checked,
    includeHidden: includeHiddenChecked(),
  };
}

function shuffle<T>(items: T[]): T[] {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

async function beginDeck(): Promise<void> {
  readSettings();
  const selected = selectedChapters();
  // Also reached from "Practice again", where deck setup is hidden: show it so these messages are seen.
  const fail = (message: string) => {
    showSetup();
    element('start-error').textContent = message;
  };
  if (!selected.length) {
    fail('Choose at least one chapter to build your deck.');
    return;
  }
  if (settings.mode === 'answer' && !recognitionConstructor()) {
    fail('Speech recognition isn’t available here. Open this app in Chrome or Safari, or choose another mode.');
    return;
  }
  element('start-error').textContent = '';
  // The microphone-typed foreground service only gets the mic if it is already granted when it starts,
  // and Android 14 forbids starting it from the background, so ask now while the app is visible.
  if (usingNativeSpeech() && settings.mode === 'answer') await ensureMicrophonePermission();
  const cards = progress.buildDeck(selected, settings.direction, settings.includeHidden);
  if (!cards.length) {
    showSetup();
    const earliest = progress.earliestHiddenUntil(selected, settings.direction);
    element('all-hidden-message').textContent = earliest === null ? 'There are no cards to practice in this selection.' : allHiddenMessage(earliest);
    element('include-and-start').hidden = earliest === null;
    element('all-hidden').hidden = false;
    return;
  }
  element('all-hidden').hidden = true;
  const items = cards.map((card): Card => ({ chapter: card.chapter, word: card.word, direction: pickDirection(card) }));
  deck = settings.shuffle ? shuffle(items) : items;
  currentIndex = 0;
  active = true;
  paused = false;
  setupView.hidden = true;
  completeView.hidden = true;
  sessionView.hidden = false;
  showCard();
}

// Starting can wait on a permission prompt, so ignore repeat taps until it finishes.
const startDeck = singleFlight(beginDeck, (busy) => {
  document.querySelectorAll<HTMLButtonElement>('.start-button, #restart-deck').forEach((button) => { button.disabled = busy; });
});

function showCard(): void {
  stopCurrent();
  if (currentIndex >= deck.length) {
    finishDeck();
    return;
  }
  revealed = false;
  failureNotice = null;
  recognitionMonitor.reset();
  const card = deck[currentIndex];
  const token = runId;
  cardShownAt = performance.now();
  element('session-mode').textContent = { flip: 'Flip cards', auto: 'Auto listen', answer: 'Speak answers' }[settings.mode];
  element('session-direction').textContent = card.direction === 'es-en' ? 'ES → EN' : 'EN → ES';
  element('progress-text').textContent = `${currentIndex + 1} / ${deck.length}`;
  element<HTMLDivElement>('progress-bar').style.width = `${((currentIndex + 1) / deck.length) * 100}%`;
  element('prompt-label').textContent = card.direction === 'es-en' ? 'SPANISH' : 'ENGLISH';
  element('card-prompt').textContent = promptFor(card);
  element('card-prompt').classList.toggle('long-text', promptFor(card).length > 45);
  element('card-answer').hidden = true;
  element('card-detail').hidden = true;
  element('flip-hint').hidden = settings.mode !== 'flip';
  element('heard-text').textContent = '';
  element('pause-button').hidden = settings.mode === 'flip';
  element('know-button').hidden = settings.mode === 'answer';
  element('pause-button').textContent = 'Pause';
  element('next-button').innerHTML = settings.mode === 'flip' ? 'Next card <span aria-hidden="true">→</span>' : 'Skip card <span aria-hidden="true">→</span>';
  setStatus(settings.mode === 'flip' ? 'Tap the card when you’re ready.' : 'Get ready to listen…');

  syncBackground();

  if (settings.mode === 'auto') void runAuto(card, token);
  if (settings.mode === 'answer') void runAnswer(card, token);
}

/** Keeps the Android foreground-service notification in step with the card on screen. */
function syncBackground(): void {
  if (!active || settings.mode === 'flip' || currentIndex >= deck.length) return;
  const card = deck[currentIndex];
  backgroundSession.sync(buildNotification({
    mode: settings.mode,
    index: currentIndex,
    total: deck.length,
    prompt: promptFor(card),
    answer: answerFor(card),
    revealed,
    paused,
    notice: failureNotice,
  }));
}

function revealAnswer(): void {
  revealed = true;
  const card = deck[currentIndex];
  const answer = element('card-answer');
  answer.textContent = answerFor(card);
  answer.hidden = false;
  const detail = [card.word.partOfSpeech, card.word.gender].filter(Boolean).join(' · ');
  element('card-detail').textContent = detail;
  element('card-detail').hidden = !detail;
  element('flip-hint').hidden = true;
  element('flashcard').classList.add('revealed');
  syncBackground();
}

function setStatus(message: string, state = ''): void {
  element('session-status').textContent = message;
  element('status-indicator').className = `status-indicator ${state}`;
}

function stopCurrent(): void {
  runId += 1;
  recognition?.abort();
  recognition = null;
  speaker.cancel();
  element('flashcard').classList.remove('revealed');
}

function nextCard(): void {
  if (!active) return;
  currentIndex += 1;
  paused = false;
  showCard();
}

/** Flip cards / Auto listen: hide this card's word in its direction, then move on (cancelling speech and timers like Skip). */
function knowIt(): void {
  if (!active || settings.mode === 'answer' || performance.now() - cardShownAt < KNOW_IT_GUARD_MS) return;
  const card = deck[currentIndex];
  progress.knowIt(card.chapter, card.word, card.direction);
  nextCard();
}

function wait(milliseconds: number, token: number): Promise<boolean> {
  return createWait({ isCancelled: () => token !== runId || !active, isPaused: () => paused })(milliseconds);
}

async function runAuto(card: Card, token: number): Promise<void> {
  setStatus('Listen to the prompt…', 'speaking');
  await speaker.speak(promptFor(card), promptLanguage(card));
  if (token !== runId || !await wait(settings.delay * 1000, token)) return;
  revealAnswer();
  setStatus('Here’s the answer.', 'speaking');
  await speaker.speak(answerFor(card), answerLanguage(card));
  if (token !== runId || !await wait(1800, token)) return;
  currentIndex += 1;
  showCard();
}

async function runAnswer(card: Card, token: number): Promise<void> {
  setStatus('Listen to the prompt…', 'speaking');
  await speaker.speak(promptFor(card), promptLanguage(card));
  if (token !== runId || !await wait(350, token)) return;
  startListening(card, token);
}

function startListening(card: Card, token: number): void {
  const Recognition = recognitionConstructor();
  if (!Recognition || paused || token !== runId) return;
  recognition?.abort();
  const current = new Recognition();
  recognition = current;
  ownAudio.touch();
  current.lang = answerLanguage(card) === 'es' ? 'es-ES' : 'en-US';
  current.continuous = false;
  current.interimResults = false;
  current.maxAlternatives = 5;
  let handled = false;
  let retryDelay = recognitionRetryDelay('no-speech');
  setStatus('Listening… say your answer.', 'listening');

  current.onresult = (event) => {
    handled = true;
    const transcripts: string[] = [];
    for (let i = 0; i < event.results.length; i++) {
      for (let j = 0; j < event.results[i].length; j++) transcripts.push(event.results[i][j].transcript);
    }
    recognitionMonitor.reset();
    const correct = transcripts.some((transcript) => isCorrectAnswer(transcript, answerFor(card)));
    element('heard-text').textContent = transcripts[0] ? `I heard: “${transcripts[0]}”` : '';
    void handleSpokenAnswer(correct, card, token);
  };
  current.onerror = (event) => {
    // An aborted recognizer (Pause, Skip, Stop) can still report late; it must not touch the current card.
    if (event.error === 'aborted' || token !== runId || !active || paused) return;
    const verdict = recognitionMonitor.handle(event.error, { native: usingNativeSpeech(), hidden: backgroundSession.isBackground() });
    retryDelay = recognitionMonitor.retryDelay(event.error);
    if (verdict === 'pause') {
      handled = true;
      pauseAfterRecognitionFailure(event.error);
    } else if (verdict === 'retry') {
      setStatus('Recognition had trouble. I’ll try listening again.');
    }
  };
  current.onend = () => {
    if (recognition === current) recognition = null; // no longer listening
    ownAudio.touch(); // the recognizer's audio-focus change can arrive after it closes
    if (!handled && token === runId && active && !paused) {
      setStatus('I didn’t catch that. Listening again…', 'listening');
      window.setTimeout(() => startListening(card, token), retryDelay);
    }
  };
  try {
    current.start();
  } catch {
    setStatus('Couldn’t start the microphone. Press Pause, then Resume to try again.');
  }
}

function pauseAfterRecognitionFailure(error: string): void {
  runId += 1; // invalidate any pending listen retry so Resume starts from a clean slate
  paused = true;
  element('pause-button').textContent = 'Resume';
  const background = backgroundSession.isBackground();
  setStatus(recognitionFailureMessage(error, background, usingNativeSpeech()));
  failureNotice = recognitionFailureNotice(error, background);
  syncBackground();
}

async function handleSpokenAnswer(correct: boolean, card: Card, token: number): Promise<void> {
  recognition?.abort();
  recognition = null;
  ownAudio.touch();
  if (token !== runId) return;
  if (correct) {
    progress.recordCorrect(card.chapter, card.word, card.direction);
    revealAnswer();
    setStatus('Correct. Nice work.', 'correct');
    await speaker.speak('Correct', 'en');
    if (await wait(900, token)) {
      currentIndex += 1;
      showCard();
    }
    return;
  }

  // One try per card: a wrong answer reveals and speaks the answer, then moves on.
  progress.recordMiss(card.chapter, card.word, card.direction);
  revealAnswer();
  setStatus('Not quite — the answer is above. Let’s keep going.');
  await speaker.speak(answerFor(card), answerLanguage(card));
  if (await wait(2800, token)) {
    currentIndex += 1;
    showCard();
  }
}

function togglePause(): void {
  if (settings.mode === 'flip') return;
  paused = !paused;
  failureNotice = null;
  element('pause-button').textContent = paused ? 'Resume' : 'Pause';
  if (paused) {
    if (settings.mode === 'answer' && !revealed) {
      runId += 1;
      speaker.cancel();
    } else {
      speaker.pause();
    }
    recognition?.abort();
    recognition = null;
    setStatus('Paused. Press Resume when you’re ready.');
  } else {
    speaker.resume();
    recognitionMonitor.reset();
    if (settings.mode === 'answer' && !revealed) {
      void runAnswer(deck[currentIndex], runId);
    } else {
      setStatus('Resumed.', settings.mode === 'auto' ? 'speaking' : '');
    }
  }
  syncBackground();
}

function finishDeck(): void {
  stopCurrent();
  active = false;
  backgroundSession.stop();
  sessionView.hidden = true;
  completeView.hidden = false;
  element('complete-summary').textContent = `You worked through ${deck.length.toLocaleString()} ${deck.length === 1 ? 'card' : 'cards'}.`;
}

/** Shows deck setup with counts re-derived from the current progress. */
function showSetup(): void {
  sessionView.hidden = true;
  completeView.hidden = true;
  setupView.hidden = false;
  refreshSetup();
}

function returnToSetup(): void {
  stopCurrent();
  active = false;
  paused = false;
  backgroundSession.stop();
  showSetup();
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  void startDeck();
});
form.addEventListener('change', (event) => {
  const target = event.target as HTMLInputElement;
  if (target.name === 'mode') {
    element('delay-setting').hidden = target.value !== 'auto';
    updateSupportNote();
  }
  if (target.name === 'direction' || target.id === 'include-hidden') refreshSetup();
});
element('master-count').addEventListener('input', (event) => {
  element('master-count-value').textContent = pluralize(Number((event.target as HTMLInputElement).value), 'correct answer');
});
element('hide-weeks').addEventListener('input', (event) => {
  element('hide-weeks-value').textContent = pluralize(Number((event.target as HTMLInputElement).value), 'week');
});
element('master-count').addEventListener('change', (event) => {
  progress.updateSettings({ masterCount: Number((event.target as HTMLInputElement).value) });
  updateMasterySettings();
});
element('hide-weeks').addEventListener('change', (event) => {
  progress.updateSettings({ hideWeeks: Number((event.target as HTMLInputElement).value) });
  updateMasterySettings();
});
element('include-and-start').addEventListener('click', () => {
  element<HTMLInputElement>('include-hidden').checked = true;
  refreshSetup();
  startDeck();
});
element('delay').addEventListener('input', () => {
  const value = Number(element<HTMLInputElement>('delay').value);
  element('delay-value').textContent = `${value} ${value === 1 ? 'second' : 'seconds'}`;
});
element('select-all').addEventListener('click', () => {
  chapterList.querySelectorAll<HTMLInputElement>('input').forEach((input) => { input.checked = true; });
  refreshSetup();
});
element('select-none').addEventListener('click', () => {
  chapterList.querySelectorAll<HTMLInputElement>('input').forEach((input) => { input.checked = false; });
  refreshSetup();
});
element('flashcard').addEventListener('click', () => {
  if (settings.mode === 'flip' && !revealed) revealAnswer();
});
element('next-button').addEventListener('click', nextCard);
element('know-button').addEventListener('click', knowIt);
element('pause-button').addEventListener('click', togglePause);
element('end-session').addEventListener('click', returnToSetup);
element('new-deck').addEventListener('click', returnToSetup);
element('restart-deck').addEventListener('click', () => { void startDeck(); });
document.addEventListener('visibilitychange', () => {
  const hiddenState = { hidden: document.hidden, active, mode: settings.mode, paused, native: usingNativeSpeech() };
  if (shouldAutoPauseWhenHidden(hiddenState)) togglePause();
});

updateMasterySettings();
// Notification buttons drive the same code paths as the on-screen controls.
void backgroundSession.onAction((action, source) => dispatchBackgroundAction(action, {
  isActive: () => active && settings.mode !== 'flip',
  isPaused: () => paused,
  isListening: () => recognition !== null,
  isOwnAudio: () => ownAudio.isActive(),
  pause: togglePause,
  resume: togglePause,
  skip: nextCard,
  stop: returnToSetup,
}, source));
void backgroundSession.watchAppState();
// Clear any notification left behind by a previous page load.
backgroundSession.stop();

void loadVocabulary();
