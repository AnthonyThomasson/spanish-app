import './style.css';
import { isCorrectAnswer } from './matching';
import { recognitionConstructor, Speaker, usingNativeSpeech, type SpeechRecognitionLike } from './speech';
import type { Chapter, Direction, Mode, Vocabulary, Word } from './types';

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
            <div class="segmented two-up">
              <label><input type="radio" name="direction" value="es-en" checked><span><b>Spanish</b><small>to English</small></span></label>
              <label><input type="radio" name="direction" value="en-es"><span><b>English</b><small>to Spanish</small></span></label>
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
          <label class="shuffle-toggle"><span><b>Shuffle deck</b><small>Mix up the card order</small></span><input id="shuffle" type="checkbox" checked><span class="switch" aria-hidden="true"></span></label>
          <p id="start-error" class="form-error" role="alert"></p>
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

let chapters: Chapter[] = [];
let deck: Word[] = [];
let currentIndex = 0;
let misses = 0;
let revealed = false;
let paused = false;
let active = false;
let runId = 0;
let recognition: SpeechRecognitionLike | null = null;
let settings = { direction: 'es-en' as Direction, mode: 'flip' as Mode, delay: 3, shuffle: true };

const promptFor = (word: Word) => settings.direction === 'es-en' ? word.spanish : word.english;
const answerFor = (word: Word) => settings.direction === 'es-en' ? word.english : word.spanish;
const promptLanguage = () => settings.direction === 'es-en' ? 'es' as const : 'en' as const;
const answerLanguage = () => settings.direction === 'es-en' ? 'en' as const : 'es' as const;

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
  chapters.forEach((chapter, index) => {
    const label = document.createElement('label');
    label.className = 'chapter-option';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = String(chapter.number);
    checkbox.checked = index === 0;
    checkbox.addEventListener('change', updateSelectionSummary);
    const number = document.createElement('span');
    number.className = 'chapter-number';
    number.textContent = String(chapter.number).padStart(2, '0');
    const title = document.createElement('span');
    title.className = 'chapter-title';
    title.textContent = chapter.title;
    const count = document.createElement('span');
    count.className = 'chapter-count';
    count.textContent = `${chapter.words.length} words`;
    label.append(checkbox, number, title, count);
    chapterList.append(label);
  });
  updateSelectionSummary();
}

function selectedChapterNumbers(): number[] {
  return Array.from(chapterList.querySelectorAll<HTMLInputElement>('input:checked')).map((input) => Number(input.value));
}

function updateSelectionSummary(): void {
  const selected = selectedChapterNumbers();
  const count = chapters.filter((chapter) => selected.includes(chapter.number)).reduce((total, chapter) => total + chapter.words.length, 0);
  element('selection-summary').textContent = `${selected.length} ${selected.length === 1 ? 'chapter' : 'chapters'} · ${count.toLocaleString()} cards`;
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

function startDeck(event?: SubmitEvent): void {
  event?.preventDefault();
  readSettings();
  const selected = selectedChapterNumbers();
  if (!selected.length) {
    element('start-error').textContent = 'Choose at least one chapter to build your deck.';
    return;
  }
  if (settings.mode === 'answer' && !recognitionConstructor()) {
    element('start-error').textContent = 'Speech recognition isn’t available here. Open this app in Chrome or Safari, or choose another mode.';
    return;
  }
  element('start-error').textContent = '';
  const words = chapters.filter((chapter) => selected.includes(chapter.number)).flatMap((chapter) => chapter.words);
  deck = settings.shuffle ? shuffle(words) : [...words];
  currentIndex = 0;
  active = true;
  paused = false;
  setupView.hidden = true;
  completeView.hidden = true;
  sessionView.hidden = false;
  showCard();
}

function showCard(): void {
  stopCurrent();
  if (currentIndex >= deck.length) {
    finishDeck();
    return;
  }
  misses = 0;
  revealed = false;
  const word = deck[currentIndex];
  const token = runId;
  element('session-mode').textContent = { flip: 'Flip cards', auto: 'Auto listen', answer: 'Speak answers' }[settings.mode];
  element('session-direction').textContent = settings.direction === 'es-en' ? 'ES → EN' : 'EN → ES';
  element('progress-text').textContent = `${currentIndex + 1} / ${deck.length}`;
  element<HTMLDivElement>('progress-bar').style.width = `${((currentIndex + 1) / deck.length) * 100}%`;
  element('prompt-label').textContent = settings.direction === 'es-en' ? 'SPANISH' : 'ENGLISH';
  element('card-prompt').textContent = promptFor(word);
  element('card-prompt').classList.toggle('long-text', promptFor(word).length > 45);
  element('card-answer').hidden = true;
  element('card-detail').hidden = true;
  element('flip-hint').hidden = settings.mode !== 'flip';
  element('heard-text').textContent = '';
  element('pause-button').hidden = settings.mode === 'flip';
  element('pause-button').textContent = 'Pause';
  element('next-button').innerHTML = settings.mode === 'flip' ? 'Next card <span aria-hidden="true">→</span>' : 'Skip card <span aria-hidden="true">→</span>';
  setStatus(settings.mode === 'flip' ? 'Tap the card when you’re ready.' : 'Get ready to listen…');

  if (settings.mode === 'auto') void runAuto(word, token);
  if (settings.mode === 'answer') void runAnswer(word, token);
}

function revealAnswer(): void {
  revealed = true;
  const word = deck[currentIndex];
  const answer = element('card-answer');
  answer.textContent = answerFor(word);
  answer.hidden = false;
  const detail = [word.partOfSpeech, word.gender].filter(Boolean).join(' · ');
  element('card-detail').textContent = detail;
  element('card-detail').hidden = !detail;
  element('flip-hint').hidden = true;
  element('flashcard').classList.add('revealed');
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

async function wait(milliseconds: number, token: number): Promise<boolean> {
  let remaining = milliseconds;
  let previous = Date.now();
  return new Promise((resolve) => {
    const tick = () => {
      if (token !== runId || !active) {
        resolve(false);
        return;
      }
      const now = Date.now();
      if (!paused) remaining -= now - previous;
      previous = now;
      if (remaining <= 0) resolve(true);
      else window.setTimeout(tick, Math.min(100, remaining));
    };
    tick();
  });
}

async function runAuto(word: Word, token: number): Promise<void> {
  setStatus('Listen to the prompt…', 'speaking');
  await speaker.speak(promptFor(word), promptLanguage());
  if (token !== runId || !await wait(settings.delay * 1000, token)) return;
  revealAnswer();
  setStatus('Here’s the answer.', 'speaking');
  await speaker.speak(answerFor(word), answerLanguage());
  if (token !== runId || !await wait(1800, token)) return;
  currentIndex += 1;
  showCard();
}

async function runAnswer(word: Word, token: number): Promise<void> {
  setStatus('Listen to the prompt…', 'speaking');
  await speaker.speak(promptFor(word), promptLanguage());
  if (token !== runId || !await wait(350, token)) return;
  startListening(word, token);
}

function startListening(word: Word, token: number): void {
  const Recognition = recognitionConstructor();
  if (!Recognition || paused || token !== runId) return;
  recognition?.abort();
  const current = new Recognition();
  recognition = current;
  current.lang = answerLanguage() === 'es' ? 'es-ES' : 'en-US';
  current.continuous = false;
  current.interimResults = false;
  current.maxAlternatives = 5;
  let handled = false;
  setStatus('Listening… say your answer.', 'listening');

  current.onresult = (event) => {
    handled = true;
    const transcripts: string[] = [];
    for (let i = 0; i < event.results.length; i++) {
      for (let j = 0; j < event.results[i].length; j++) transcripts.push(event.results[i][j].transcript);
    }
    const correct = transcripts.some((transcript) => isCorrectAnswer(transcript, answerFor(word)));
    element('heard-text').textContent = transcripts[0] ? `I heard: “${transcripts[0]}”` : '';
    void handleSpokenAnswer(correct, word, token);
  };
  current.onerror = (event) => {
    if (event.error === 'aborted') return;
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      handled = true;
      paused = true;
      element('pause-button').textContent = 'Resume';
      setStatus('Microphone access is blocked. Allow it in your browser settings, then press Resume.');
    } else if (event.error !== 'no-speech') {
      setStatus('Recognition had trouble. I’ll try listening again.');
    }
  };
  current.onend = () => {
    if (!handled && token === runId && active && !paused) {
      setStatus('I didn’t catch that. Listening again…', 'listening');
      window.setTimeout(() => startListening(word, token), 250);
    }
  };
  try {
    current.start();
  } catch {
    setStatus('Couldn’t start the microphone. Press Pause, then Resume to try again.');
  }
}

async function handleSpokenAnswer(correct: boolean, word: Word, token: number): Promise<void> {
  recognition?.abort();
  recognition = null;
  if (token !== runId) return;
  if (correct) {
    revealAnswer();
    setStatus('Correct. Nice work.', 'correct');
    await speaker.speak('Correct', 'en');
    if (await wait(900, token)) {
      currentIndex += 1;
      showCard();
    }
    return;
  }

  misses += 1;
  if (misses >= 3) {
    revealAnswer();
    setStatus('The answer is above. Let’s keep going.');
    await speaker.speak(answerFor(word), answerLanguage());
    if (await wait(2800, token)) {
      currentIndex += 1;
      showCard();
    }
    return;
  }
  setStatus(`Not quite — try again. ${3 - misses} ${3 - misses === 1 ? 'try' : 'tries'} before I reveal it.`);
  await speaker.speak('Try again', 'en');
  if (token === runId && !paused) startListening(word, token);
}

function togglePause(): void {
  if (settings.mode === 'flip') return;
  paused = !paused;
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
    if (settings.mode === 'answer' && !revealed) {
      void runAnswer(deck[currentIndex], runId);
    } else {
      setStatus('Resumed.', settings.mode === 'auto' ? 'speaking' : '');
    }
  }
}

function finishDeck(): void {
  stopCurrent();
  active = false;
  sessionView.hidden = true;
  completeView.hidden = false;
  element('complete-summary').textContent = `You worked through ${deck.length.toLocaleString()} ${deck.length === 1 ? 'card' : 'cards'}.`;
}

function returnToSetup(): void {
  stopCurrent();
  active = false;
  paused = false;
  sessionView.hidden = true;
  completeView.hidden = true;
  setupView.hidden = false;
}

form.addEventListener('submit', startDeck);
form.addEventListener('change', (event) => {
  const target = event.target as HTMLInputElement;
  if (target.name === 'mode') {
    element('delay-setting').hidden = target.value !== 'auto';
    updateSupportNote();
  }
});
element('delay').addEventListener('input', () => {
  const value = Number(element<HTMLInputElement>('delay').value);
  element('delay-value').textContent = `${value} ${value === 1 ? 'second' : 'seconds'}`;
});
element('select-all').addEventListener('click', () => {
  chapterList.querySelectorAll('input').forEach((input) => { (input as HTMLInputElement).checked = true; });
  updateSelectionSummary();
});
element('select-none').addEventListener('click', () => {
  chapterList.querySelectorAll('input').forEach((input) => { (input as HTMLInputElement).checked = false; });
  updateSelectionSummary();
});
element('flashcard').addEventListener('click', () => {
  if (settings.mode === 'flip' && !revealed) revealAnswer();
});
element('next-button').addEventListener('click', nextCard);
element('pause-button').addEventListener('click', togglePause);
element('end-session').addEventListener('click', returnToSetup);
element('new-deck').addEventListener('click', returnToSetup);
element('restart-deck').addEventListener('click', () => startDeck());
document.addEventListener('visibilitychange', () => {
  if (document.hidden && active && settings.mode !== 'flip' && !paused) togglePause();
});

void loadVocabulary();
