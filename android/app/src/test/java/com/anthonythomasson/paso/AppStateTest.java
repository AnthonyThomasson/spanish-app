package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class AppStateTest {

    @Test
    public void startsInTheForeground() {
        assertFalse(new AppState().isBackground());
    }

    @Test
    public void pauseAndResumeToggleBackground() {
        AppState state = new AppState();
        state.onPause();
        assertTrue(state.isBackground());
        state.onResume();
        assertFalse(state.isBackground());
    }

    @Test
    public void eventNameMatchesTheJsContract() {
        assertEquals("appState", AppState.EVENT);
    }
}
