package com.anthonythomasson.paso;

import android.media.AudioManager;

/** Decides how the session reacts to audio focus changes. */
final class AudioFocusPolicy {

    private AudioFocusPolicy() {}

    /**
     * Losing focus (permanently, or transiently e.g. a phone call) pauses the session. Ducking is
     * ignored, and regaining focus never resumes: the user resumes explicitly.
     */
    static SessionAction actionFor(int focusChange) {
        switch (focusChange) {
            case AudioManager.AUDIOFOCUS_LOSS:
            case AudioManager.AUDIOFOCUS_LOSS_TRANSIENT:
                return SessionAction.PAUSE;
            default:
                return null;
        }
    }

    /** A transient loss (as opposed to a permanent {@code AUDIOFOCUS_LOSS}): the kind our own speech and recognizer cause. */
    static boolean isTransientLoss(int focusChange) {
        return focusChange == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT;
    }

    /** Whether the audio mode says a call is ringing or in progress (including VoIP). */
    static boolean isCallMode(int audioMode) {
        return audioMode == AudioManager.MODE_RINGTONE
            || audioMode == AudioManager.MODE_IN_CALL
            || audioMode == AudioManager.MODE_IN_COMMUNICATION;
    }
}
