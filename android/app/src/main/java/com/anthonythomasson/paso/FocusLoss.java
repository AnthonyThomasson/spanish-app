package com.anthonythomasson.paso;

/** What kind of audio-focus loss paused the session; sent to JS so it can tell our own speech from another app. */
final class FocusLoss {

    final int focusChange;
    /** The device is ringing or in a call (including a VoIP call): a real interruption whatever else is playing. */
    final boolean call;

    FocusLoss(int focusChange, boolean call) {
        this.focusChange = focusChange;
        this.call = call;
    }

    /** A transient loss is what our own text-to-speech and speech recognizer cause; a permanent one never is. */
    boolean isTransient() {
        return AudioFocusPolicy.isTransientLoss(focusChange);
    }
}
