# AGENTS.md — spanish-app

A Spanish learning app built with Vite, TypeScript, and Capacitor Android. Run it with `npm run dev`; use `npm run dev:phone` for HTTPS on a phone. Generate the required local vocabulary with `uv run scripts/extract_vocab.py "/path/to/book.pdf"` (macOS/Swift/uv required). Build the offline Android APK with `npm run android:apk` and serve it with `npm run android:serve`. Never commit `data/vocab.json`, `extraction/`, or `release/`; they contain copyrighted book material.

**Issue tracker:** GitHub Issues on `AnthonyThomasson/spanish-app`.

This repository is public. Never commit secrets, API keys, or `.env` files.
