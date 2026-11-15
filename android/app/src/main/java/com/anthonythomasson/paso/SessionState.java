package com.anthonythomasson.paso;

/** Immutable description of what the session notification should show. */
public final class SessionState {

    public static final String DEFAULT_TITLE = "Paso";

    private final String title;
    private final String text;
    private final boolean paused;
    private final SessionMode mode;

    public SessionState(String title, String text, boolean paused) {
        this(title, text, paused, SessionMode.AUTO);
    }

    public SessionState(String title, String text, boolean paused, SessionMode mode) {
        this.mode = mode == null ? SessionMode.AUTO : mode;
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

    public SessionMode mode() {
        return mode;
    }

    /** New notification content for the same session: the mode chosen at start() never changes. */
    public SessionState withContent(String title, String text, boolean paused) {
        return new SessionState(title, text, paused, mode);
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
