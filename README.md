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

Then open `http://<mac-wifi-ip>:8787/spanish-app.apk` on the phone, or scan the generated `release/qr.png`. On the Samsung, allow the browser to install unknown apps if Android asks, open the downloaded APK, and install it. The APK is debug-signed for personal installation, not for Play Store distribution.

The `release/` directory is ignored by Git because the APK contains the copyrighted vocabulary. Do not upload the APK or QR code publicly.
