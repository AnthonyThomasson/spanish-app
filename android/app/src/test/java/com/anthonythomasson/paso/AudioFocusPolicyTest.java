package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import android.media.AudioManager;
import org.junit.Test;

public class AudioFocusPolicyTest {

    @Test
    public void permanentLossPauses() {
        assertEquals(SessionAction.PAUSE, AudioFocusPolicy.actionFor(AudioManager.AUDIOFOCUS_LOSS));
    }

    @Test
    public void transientLossPauses() {
        assertEquals(SessionAction.PAUSE, AudioFocusPolicy.actionFor(AudioManager.AUDIOFOCUS_LOSS_TRANSIENT));
    }

    @Test
    public void duckingIsNotALossBecauseWeNeverAutoResume() {
        assertNull(AudioFocusPolicy.actionFor(AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK));
    }

    @Test
    public void gainNeverResumesAutomatically() {
        assertNull(AudioFocusPolicy.actionFor(AudioManager.AUDIOFOCUS_GAIN));
    }

    @Test
    public void onlyTheTransientLossCanBeOurOwnSpeech() {
        assertTrue(AudioFocusPolicy.isTransientLoss(AudioManager.AUDIOFOCUS_LOSS_TRANSIENT));
        assertFalse(AudioFocusPolicy.isTransientLoss(AudioManager.AUDIOFOCUS_LOSS));
        assertFalse(new FocusLoss(AudioManager.AUDIOFOCUS_LOSS, false).isTransient());
        assertTrue(new FocusLoss(AudioManager.AUDIOFOCUS_LOSS_TRANSIENT, false).isTransient());
    }

    @Test
    public void ringingOrInACallCountsAsACall() {
        assertTrue(AudioFocusPolicy.isCallMode(AudioManager.MODE_RINGTONE));
        assertTrue(AudioFocusPolicy.isCallMode(AudioManager.MODE_IN_CALL));
        assertTrue(AudioFocusPolicy.isCallMode(AudioManager.MODE_IN_COMMUNICATION));
    }

    @Test
    public void normalAudioIsNotACall() {
        assertFalse(AudioFocusPolicy.isCallMode(AudioManager.MODE_NORMAL));
        assertFalse(AudioFocusPolicy.isCallMode(AudioManager.MODE_CALL_SCREENING));
    }
}
