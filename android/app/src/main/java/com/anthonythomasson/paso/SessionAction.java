package com.anthonythomasson.paso;

/** Actions a user can trigger from the session notification (or that the native side raises itself). */
public enum SessionAction {
    PAUSE("pause"),
    RESUME("resume"),
    SKIP("skip"),
    STOP("stop");

    private static final String INTENT_PREFIX = "com.anthonythomasson.paso.action.";

    private final String wireName;

    SessionAction(String wireName) {
        this.wireName = wireName;
    }

    /** The value delivered to JS in the "action" event. */
    public String wireName() {
        return wireName;
    }

    /** The Intent action used by notification buttons. */
    public String intentAction() {
        return INTENT_PREFIX + name();
    }

    public static SessionAction fromIntentAction(String intentAction) {
        if (intentAction == null) {
            return null;
        }
        for (SessionAction action : values()) {
            if (action.intentAction().equals(intentAction)) {
                return action;
            }
        }
        return null;
    }
}
