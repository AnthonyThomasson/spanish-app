package com.anthonythomasson.paso;

/** Immutable description of what the session notification should show. */
public final class SessionState {

    public static final String DEFAULT_TITLE = "Paso";

    private final String title;
    private final String text;
    private final boolean paused;

    public SessionState(String title, String text, boolean paused) {
        this.title = isBlank(title) ? DEFAULT_TITLE : title;
        this.text = isBlank(text) ? "" : text;
        this.paused = paused;
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

    /** The action the first button performs: Pause while running, Resume while paused. */
    public SessionAction toggleAction() {
        return paused ? SessionAction.RESUME : SessionAction.PAUSE;
    }

    /** Nothing is running while paused, so the partial wake lock is only needed otherwise. */
    public boolean needsWakeLock() {
        return !paused;
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
