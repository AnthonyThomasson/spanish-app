package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Before;
import org.junit.Test;

public class SessionRegistryTest {

    @Before
    public void reset() {
        SessionRegistry.end();
    }

    @Test
    public void beginMarksTheSessionActive() {
        assertFalse(SessionRegistry.isActive());
        SessionRegistry.begin();
        assertTrue(SessionRegistry.isActive());
    }

    @Test
    public void beginWhileActiveKeepsTheSameGeneration() {
        int first = SessionRegistry.begin();
        assertEquals(first, SessionRegistry.begin());
    }

    @Test
    public void aNewSessionAfterEndGetsANewGeneration() {
        int first = SessionRegistry.begin();
        SessionRegistry.end();
        assertNotEquals(first, SessionRegistry.begin());
    }

    @Test
    public void endIfCurrentEndsTheOwnSession() {
        int generation = SessionRegistry.begin();
        assertTrue(SessionRegistry.endIfCurrent(generation));
        assertFalse(SessionRegistry.isActive());
    }

    @Test
    public void aStaleInstanceCannotEndANewerSession() {
        int old = SessionRegistry.begin();
        SessionRegistry.end(); // stop()
        SessionRegistry.begin(); // new session started right after
        assertFalse(SessionRegistry.endIfCurrent(old)); // old instance's late onTaskRemoved
        assertTrue(SessionRegistry.isActive());
    }
}
