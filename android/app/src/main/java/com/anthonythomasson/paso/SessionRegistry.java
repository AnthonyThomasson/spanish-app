package com.anthonythomasson.paso;

/**
 * Process-wide record of whether a session is active and which one. Each session gets a generation
 * so a late callback from an old service instance cannot end a session that was started after it.
 */
final class SessionRegistry {

    private static boolean active;
    private static int generation;

    private SessionRegistry() {}

    /** Starts a session (or joins the active one) and returns its generation. */
    static synchronized int begin() {
        if (!active) {
            active = true;
            generation++;
        }
        return generation;
    }

    /** Ends whatever session is active, unconditionally (plugin stop / failure paths). */
    static synchronized void end() {
        active = false;
    }

    /** Ends the session only if it is still the given generation; returns whether it was ended. */
    static synchronized boolean endIfCurrent(int sessionGeneration) {
        if (active && generation == sessionGeneration) {
            active = false;
            return true;
        }
        return false;
    }

    static synchronized boolean isActive() {
        return active;
    }

    static synchronized int generation() {
        return generation;
    }
}
