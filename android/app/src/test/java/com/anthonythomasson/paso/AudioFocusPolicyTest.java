package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

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
}
