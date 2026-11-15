package com.anthonythomasson.paso;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.content.pm.ServiceInfo;
import org.junit.Test;

public class ForegroundPromotionTest {

    private static final int MEDIA = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK;
    private static final int MIC = ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;

    @Test
    public void promotesWhenTheServiceIsNotYetForeground() {
        assertTrue(ForegroundPromotion.shouldPromote(false, 0, MEDIA | MIC));
    }

    @Test
    public void justRepostsTheNotificationWhenTypesAreUnchanged() {
        assertFalse(ForegroundPromotion.shouldPromote(true, MEDIA | MIC, MEDIA | MIC));
    }

    @Test
    public void promotesAgainWhenANewTypeIsNeeded() {
        assertTrue(ForegroundPromotion.shouldPromote(true, MEDIA, MEDIA | MIC));
    }

    @Test
    public void neverDowngradesARunningServiceWhoseMicrophoneTypeIsNoLongerResolved() {
        assertFalse(ForegroundPromotion.shouldPromote(true, MEDIA | MIC, MEDIA));
    }

    @Test
    public void noTypesBeforeApi29NeverRepromotes() {
        assertFalse(ForegroundPromotion.shouldPromote(true, 0, 0));
    }
}
