package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class SessionSourceTest {

    @Test
    public void wireNamesMatchTheJsContract() {
        assertEquals("notification", SessionSource.NOTIFICATION.wireName());
        assertEquals("audio-focus", SessionSource.AUDIO_FOCUS.wireName());
    }
}
