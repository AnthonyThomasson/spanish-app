package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;

import android.content.pm.ServiceInfo;
import org.junit.Test;

public class ForegroundTypesTest {

    private static final int MEDIA = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK;
    private static final int MIC = ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;

    @Test
    public void usesMediaPlaybackAndMicrophoneWhenRecordAudioGranted() {
        assertEquals(MEDIA | MIC, ForegroundTypes.resolve(34, true, SessionMode.ANSWER));
    }

    @Test
    public void dropsMicrophoneWhenRecordAudioNotGrantedToAvoidSecurityException() {
        assertEquals(MEDIA, ForegroundTypes.resolve(34, false, SessionMode.ANSWER));
    }

    @Test
    public void microphoneTypeDoesNotExistBeforeApi30() {
        assertEquals(MEDIA, ForegroundTypes.resolve(29, true, SessionMode.ANSWER));
    }

    @Test
    public void noTypesBeforeApi29() {
        assertEquals(0, ForegroundTypes.resolve(28, true, SessionMode.ANSWER));
    }

    @Test
    public void autoListenNeverGetsTheMicrophoneTypeEvenWhenGranted() {
        assertEquals(MEDIA, ForegroundTypes.resolve(34, true, SessionMode.AUTO));
    }
}
