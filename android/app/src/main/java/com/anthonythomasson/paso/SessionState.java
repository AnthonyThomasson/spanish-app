package com.anthonythomasson.paso;

/** Immutable description of what the session notification should show. */
public final class SessionState {

    public static final String DEFAULT_TITLE = "Paso";
    public static final String DEFAULT_MODE = "auto";

    private final String title;
    private final String text;
    private final boolean paused;
    private final String mode;

    public SessionState(String title, String text, boolean paused, String mode) {
        this.title = isBlank(title) ? DEFAULT_TITLE : title;
        this.text = isBlank(text) ? "" : text;
        this.paused = paused;
        this.mode = isBlank(mode) ? DEFAULT_MODE : mode;
    }

    public String title() {
        return title;
    }

    public String text() {
        return text;
    }

    public boolean paused() {
        return paused;
    }

    public String mode() {
        return mode;
    }

    /** The action the first button performs: Pause while running, Resume while paused. */
    public SessionAction toggleAction() {
        return paused ? SessionAction.RESUME : SessionAction.PAUSE;
    }

    public SessionState updated(String newTitle, String newText, boolean newPaused) {
        return new SessionState(newTitle, newText, newPaused, mode);
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
