package com.anthonythomasson.paso;

/** Bridge between the foreground service (notification buttons, audio focus) and the Capacitor plugin. */
final class SessionEvents {

    interface Listener {
        /** @param source where the action came from; null for system-initiated stops (give-up, task removed). */
        void onAction(SessionAction action, SessionSource source);
    }

    private static volatile Listener listener;

    private SessionEvents() {}

    static void setListener(Listener newListener) {
        listener = newListener;
    }

    /** Clears the listener only if it is still the given one (a recreated plugin may have replaced it). */
    static void clearListener(Listener old) {
        if (listener == old) {
            listener = null;
        }
    }

    static void dispatch(SessionAction action, SessionSource source) {
        Listener current = listener;
        if (current != null) {
            current.onAction(action, source);
        }
    }
}
