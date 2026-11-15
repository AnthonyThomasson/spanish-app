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
}
