package com.anthonythomasson.paso;

import android.content.pm.ServiceInfo;

/** Chooses the foreground service type bitmask to pass to startForeground. */
final class ForegroundTypes {

    private ForegroundTypes() {}

    /**
     * mediaPlayback always; microphone only for a mode that listens (Speak answers) when RECORD_AUDIO
     * is granted (Android 14+ throws a SecurityException when starting a microphone-type service
     * without it) and the type exists (API 30+). Auto listen never claims the microphone. Before
     * API 29 foreground types are not supported, so 0 is returned.
     */
    static int resolve(int sdkInt, boolean recordAudioGranted, SessionMode mode) {
        if (sdkInt < 29) {
            return 0;
        }
        int types = ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK;
        if (sdkInt >= 30 && recordAudioGranted && mode.usesMicrophone()) {
            types |= ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
        }
        return types;
    }
}
