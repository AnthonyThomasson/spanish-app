package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class SessionModeTest {

    @Test
    public void parsesTheWireNamesUsedByJs() {
        assertEquals(SessionMode.ANSWER, SessionMode.fromWireName("answer"));
        assertEquals(SessionMode.AUTO, SessionMode.fromWireName("auto"));
    }

    @Test
    public void unknownOrMissingModeGetsTheLeastPrivilegeMode() {
        assertEquals(SessionMode.AUTO, SessionMode.fromWireName(null));
        assertEquals(SessionMode.AUTO, SessionMode.fromWireName("flip"));
    }

    @Test
    public void onlySpeakAnswersNeedsTheMicrophone() {
        assertTrue(SessionMode.ANSWER.usesMicrophone());
        assertFalse(SessionMode.AUTO.usesMicrophone());
    }
}
