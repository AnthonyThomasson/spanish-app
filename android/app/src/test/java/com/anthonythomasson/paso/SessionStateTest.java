package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class SessionStateTest {

    @Test
    public void pauseButtonShowsPauseWhileRunning() {
        SessionState state = new SessionState("Auto listen", "hola", false, "auto");
        assertEquals(SessionAction.PAUSE, state.toggleAction());
    }

    @Test
    public void pauseButtonBecomesResumeWhilePaused() {
        SessionState state = new SessionState("Auto listen", "hola", true, "auto");
        assertEquals(SessionAction.RESUME, state.toggleAction());
    }

    @Test
    public void blankTitleAndTextFallBackToDefaults() {
        SessionState state = new SessionState(null, "  ", false, null);
        assertEquals(SessionState.DEFAULT_TITLE, state.title());
        assertEquals("", state.text());
        assertEquals("auto", state.mode());
    }

    @Test
    public void withTextUpdatesTitleTextAndPausedButKeepsMode() {
        SessionState state = new SessionState("A", "b", false, "answer");
        SessionState next = state.updated("C", "d", true);
        assertEquals("C", next.title());
        assertEquals("d", next.text());
        assertTrue(next.paused());
        assertEquals("answer", next.mode());
        assertFalse(state.paused());
    }
}
