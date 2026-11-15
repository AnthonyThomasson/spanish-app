package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class SessionActionTest {

    @Test
    public void wireNamesMatchTheJsContract() {
        assertEquals("pause", SessionAction.PAUSE.wireName());
        assertEquals("resume", SessionAction.RESUME.wireName());
        assertEquals("skip", SessionAction.SKIP.wireName());
        assertEquals("stop", SessionAction.STOP.wireName());
    }

    @Test
    public void intentActionsRoundTrip() {
        for (SessionAction action : SessionAction.values()) {
            assertEquals(action, SessionAction.fromIntentAction(action.intentAction()));
        }
    }

    @Test
    public void intentActionsAreNamespacedToThePackage() {
        assertEquals("com.anthonythomasson.paso.action.PAUSE", SessionAction.PAUSE.intentAction());
    }

    @Test
    public void unknownOrNullIntentActionsMapToNull() {
        assertNull(SessionAction.fromIntentAction("android.intent.action.MAIN"));
        assertNull(SessionAction.fromIntentAction(null));
    }

    @Test
    public void onlyResumeNeedsTheCpuAndAudioFocusBeforeJsRuns() {
        assertTrue(SessionAction.RESUME.needsResourcesBeforeForwarding());
        assertFalse(SessionAction.PAUSE.needsResourcesBeforeForwarding());
        assertFalse(SessionAction.SKIP.needsResourcesBeforeForwarding());
        assertFalse(SessionAction.STOP.needsResourcesBeforeForwarding());
    }
}
