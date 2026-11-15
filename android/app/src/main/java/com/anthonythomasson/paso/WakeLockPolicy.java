package com.anthonythomasson.paso;

/** Timeouts for the session's partial wake lock. */
final class WakeLockPolicy {

    private WakeLockPolicy() {}

    /** Safety net so a leaked lock cannot drain the battery forever; refreshed on every update. */
    static final long SESSION_TIMEOUT_MS = 6L * 60 * 60 * 1000;

    /**
     * Bridges the gap between a notification Resume and JS calling update(paused=false), which then
     * takes the session lock. Short so it is released if JS never answers.
     */
    static final long RESUME_HANDOFF_TIMEOUT_MS = 30_000L;

    /** A lock that is already held has the longer session timeout; the handoff must not shorten it. */
    static boolean shouldAcquireHandoff(boolean alreadyHeld) {
        return !alreadyHeld;
    }
}
