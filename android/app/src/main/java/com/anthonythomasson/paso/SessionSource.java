package com.anthonythomasson.paso;

/** Where an action event came from; sent to JS so it can tell a user tap from a system-initiated pause. */
public enum SessionSource {
    NOTIFICATION("notification"),
    AUDIO_FOCUS("audio-focus");

    private final String wireName;

    SessionSource(String wireName) {
        this.wireName = wireName;
    }

    public String wireName() {
        return wireName;
    }
}
