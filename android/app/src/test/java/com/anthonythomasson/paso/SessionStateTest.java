package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class SessionStateTest {

    @Test
    public void pauseButtonShowsPauseWhileRunning() {
        SessionState state = new SessionState("Auto listen", "hola", false);
        assertEquals(SessionAction.PAUSE, state.toggleAction());
    }

    @Test
    public void pauseButtonBecomesResumeWhilePaused() {
        SessionState state = new SessionState("Auto listen", "hola", true);
        assertEquals(SessionAction.RESUME, state.toggleAction());
    }

    @Test
    public void blankTitleAndTextFallBackToDefaults() {
        SessionState state = new SessionState(null, "  ", false);
        assertEquals(SessionState.DEFAULT_TITLE, state.title());
        assertEquals("", state.text());
    }

    @Test
    public void wakeLockIsHeldOnlyWhileRunning() {
        assertTrue(new SessionState("t", "x", false).needsWakeLock());
        assertFalse(new SessionState("t", "x", true).needsWakeLock());
    }

    @Test
    public void modeDefaultsToAutoListen() {
        assertEquals(SessionMode.AUTO, new SessionState("t", "x", false).mode());
    }

    @Test
    public void keepsTheModeItWasStartedWith() {
        SessionState started = new SessionState("t", "x", false, SessionMode.ANSWER);
        assertEquals(SessionMode.ANSWER, started.mode());
    }

    @Test
    public void updatingTheContentKeepsTheMode() {
        SessionState updated = new SessionState("t", "x", false, SessionMode.ANSWER).withContent("t2", "y", true);
        assertEquals(SessionMode.ANSWER, updated.mode());
        assertEquals("t2", updated.title());
        assertEquals("y", updated.text());
        assertTrue(updated.paused());
    }
}
