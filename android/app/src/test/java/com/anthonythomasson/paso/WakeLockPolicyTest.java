package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class WakeLockPolicyTest {

    @Test
    public void resumeHandoffIsShortSoItIsReleasedIfJsNeverAnswers() {
        assertEquals(30_000L, WakeLockPolicy.RESUME_HANDOFF_TIMEOUT_MS);
        assertTrue(WakeLockPolicy.RESUME_HANDOFF_TIMEOUT_MS < WakeLockPolicy.SESSION_TIMEOUT_MS);
    }

    @Test
    public void sessionLockKeepsTheSixHourSafetyNet() {
        assertEquals(6L * 60 * 60 * 1000, WakeLockPolicy.SESSION_TIMEOUT_MS);
    }

    @Test
    public void handoffNeverShortensALockThatIsAlreadyHeld() {
        assertTrue(WakeLockPolicy.shouldAcquireHandoff(false));
        assertEquals(false, WakeLockPolicy.shouldAcquireHandoff(true));
    }
}
