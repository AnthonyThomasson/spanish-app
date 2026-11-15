package com.anthonythomasson.paso;

/**
 * Whether the activity is in the background. JS can't use document.hidden for this because the
 * plugin deliberately keeps the WebView looking visible while a session runs.
 */
final class AppState {

    /** Name of the Capacitor event (and the shape of getState()): { background: boolean }. */
    static final String EVENT = "appState";

    private volatile boolean background;

    void onPause() {
        background = true;
    }

    void onResume() {
        background = false;
    }

    boolean isBackground() {
        return background;
    }
}
