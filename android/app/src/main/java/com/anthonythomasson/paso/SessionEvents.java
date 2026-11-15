package com.anthonythomasson.paso;

/** Bridge between the foreground service (notification buttons, audio focus) and the Capacitor plugin. */
final class SessionEvents {

    interface Listener {
        void onAction(SessionAction action);
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

    static void dispatch(SessionAction action) {
        Listener current = listener;
        if (current != null) {
            current.onAction(action);
        }
    }
}
