# Paso — Spanish flashcards

A lightweight Vite + TypeScript flashcard app for vocabulary from a personal copy of Bárbara Bregstein’s *Complete Spanish Step-by-Step*.

## Run locally

Prerequisites: Node.js 22.12+ and npm. Extracting the vocabulary also requires macOS, Swift, and [uv](https://docs.astral.sh/uv/).

1. Install the app dependencies:

   ```sh
   npm install
   ```

2. Generate the vocabulary from your own PDF:

   ```sh
   uv run scripts/extract_vocab.py "/path/to/Complete Spanish Step-by-Step.pdf"
   ```

   The script uses `pypdf` to extract the embedded table images and macOS Vision to OCR them. It writes `data/vocab.json`; OCR intermediates go in `extraction/`. Both paths are ignored by Git. Use `--refresh-ocr` to run recognition again instead of using the cached OCR output.

3. Start the app:

   ```sh
   npm run dev
   ```

   Open the local URL printed by Vite.

## Practice modes

- Select any combination of chapters, Spanish-to-English, English-to-Spanish, or Both (each card’s direction is picked at random, so the two are mixed), and shuffled or book order.
- **Flip cards:** tap or click a card to reveal its answer.
- **Auto listen:** hear the prompt, pause for the configurable thinking time, hear the answer, and advance automatically. Pause/resume and skip are available.
- **Speak answers:** answer aloud to advance. Matching ignores case, accents, punctuation, leading articles, and “to” before verbs. Alternate meanings and optional parenthetical text are accepted. Three misses reveal the answer.

Spanish prompts use an `es-ES`/`es-MX` voice when available; English uses an English voice. Speech recognition requires Chrome or Safari and microphone permission. Recognition may use the browser vendor’s speech service; the vocabulary itself stays local.

### Use an Android phone

Microphone access generally requires HTTPS. Start the secure development server:

```sh
npm run dev:phone
```

On the same Wi-Fi network, open the **Network** `https://` URL printed by Vite. The development certificate is self-signed, so accept the browser warning and allow microphone access. Chrome is recommended.

## Build

```sh
npm run build
npm run preview
```

The build copies the locally generated vocabulary into `dist/data/vocab.json`. Do not publish that build or commit the generated data: the book’s vocabulary is copyrighted and this public repository contains only the extraction tooling and app code.

## Installable Android app

The Capacitor Android app includes the vocabulary in its local assets, so it works entirely offline after installation. On Android it uses native text-to-speech and speech recognition; the browser continues to use the Web Speech API. Microphone permission is requested when spoken-answer mode first listens.

Building requires JDK 21, the Android SDK, platform-tools, build-tools, and the Android 36 platform. `scripts/android-env.sh` detects the standard Homebrew locations on this Mac; set `JAVA_HOME` and `ANDROID_HOME` yourself on other machines.

Build and copy the debug-signed APK:

```sh
npm run android:apk
```

The output is `release/spanish-app.apk`. Serve that folder on the local network:

```sh
npm run android:serve
```

Then open `http://<mac-wifi-ip>:8787/spanish-app.apk` on the phone. On the Samsung, allow the browser to install unknown apps if Android asks, open the downloaded APK, and install it. The APK is debug-signed for personal installation, not for Play Store distribution.

### One-step install: the Phone button

`npm run phone` (also the **Phone** button in Herdr, defined in `.herdr/config.yaml`) does the whole flow:

1. runs `npm ci` if `node_modules` is missing;
2. copies `data/vocab.json` from the main checkout if this worktree lacks it (if neither has one it stops and tells you to run `uv run scripts/extract_vocab.py`);
3. builds the APK with `npm run android:apk`;
4. serves `release/` on the Mac's Wi-Fi address at port 8787, or the next free port if another worktree is already serving;
5. prints the install URL and a QR code in the terminal, and writes `release/qr.png`.

Scan the QR code with the phone (on the same Wi-Fi) and open the downloaded APK. Press Ctrl+C to stop serving. `npm run android:apk` and `npm run android:serve` still work on their own.

`npm test` runs the unit tests for the script's helper logic with Node's built-in test runner.

### Background sessions

On Android, **Auto listen** and **Speak answers** keep running when you switch apps or turn the screen off or lock the phone. While a session runs, a foreground-service notification shows the mode and progress (for example `Auto listen · 12 / 80`), the current prompt, and the answer once it is revealed. Android 13+ asks for notification permission the first time; if you decline, the session still runs in the background but the notification may be hidden.

The notification has the same controls as the screen:

- **Pause / Resume** pauses or resumes the session.
- **Skip** moves to the next card. Like the on-screen Skip, skipping while paused resumes playback on the next card.
- **Stop** ends the session and returns to deck setup.

The session also pauses itself (and never resumes on its own) when another app takes audio focus, such as a phone call. The notification then shows Resume. Speak answers ignores the brief audio-focus change caused by its own speech recognizer while it is listening.

Speak answers asks for microphone permission before the session starts, while the app is visible, so the background service can use the microphone. Android 14 and later do not allow starting a microphone service from the background. Auto listen never claims the microphone: its service only plays audio.

Flip cards is not a background session and does not use the service. In a browser, Auto listen and Speak answers still pause when the tab is hidden.

Speak answers needs the microphone, and Android may refuse microphone access to an app that is not in the foreground. If speech recognition fails in the background (microphone access blocked, repeated start failures, or several attempts in a row that hear nothing while the app is in the background), the session pauses and both the screen and the notification say why (for example “Microphone blocked in the background — open the app and press Resume”), with a Resume button; open the app and press Resume to continue. Temporary network, busy-recognizer or client errors are retried quietly and do not pause the session. Auto listen does not use the microphone and is unaffected.

The `release/` directory is ignored by Git because the APK contains the copyrighted vocabulary. Do not upload the APK or QR code publicly.
