package com.anthonythomasson.paso;

/** Which practice mode the session was started for; decides what the foreground service may claim. */
public enum SessionMode {
    AUTO("auto", false),
    ANSWER("answer", true);

    private final String wireName;
    private final boolean usesMicrophone;

    SessionMode(String wireName, boolean usesMicrophone) {
        this.wireName = wireName;
        this.usesMicrophone = usesMicrophone;
    }

    /** Only Speak answers listens; Auto listen just plays audio. */
    public boolean usesMicrophone() {
        return usesMicrophone;
    }

    /** Parses the mode JS sends to start(); anything unknown gets the least privileged mode. */
    public static SessionMode fromWireName(String name) {
        for (SessionMode mode : values()) {
            if (mode.wireName.equals(name)) {
                return mode;
            }
        }
        return AUTO;
    }

    public String wireName() {
        return wireName;
    }
}
