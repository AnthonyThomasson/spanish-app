package com.anthonythomasson.paso;

import android.speech.SpeechRecognizer;

/**
 * Rejection messages for {@link OwnMicRecognitionPlugin}. They reuse the wording of
 * {@code @capacitor-community/speech-recognition} so {@code classifyNativeRecognitionError} in
 * {@code src/recognition-errors.ts} maps both plugins the same way.
 */
final class RecognizerErrors {

    private RecognizerErrors() {}

    static final String NO_SPEECH = "No speech input";
    static final String MIC_SILENCED = "Microphone silenced by Android";
    static final String RECORDING_FAILED = "Audio recording error";
    static final String TIMEOUT = "Network timeout";
    static final String ABORTED = "Aborted";

    static String text(int code) {
        switch (code) {
            case SpeechRecognizer.ERROR_AUDIO:
                return RECORDING_FAILED;
            case SpeechRecognizer.ERROR_CLIENT:
                return "Client side error";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                return "Insufficient permissions";
            case SpeechRecognizer.ERROR_NETWORK:
                return "Network error";
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                return TIMEOUT;
            case SpeechRecognizer.ERROR_NO_MATCH:
                return "No match";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                return "RecognitionService busy";
            case SpeechRecognizer.ERROR_SERVER:
                return "error from server";
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return NO_SPEECH;
            case SpeechRecognizer.ERROR_TOO_MANY_REQUESTS:
                return "RecognitionService busy (too many requests)";
            case SpeechRecognizer.ERROR_SERVER_DISCONNECTED:
                return "Recognition service disconnected";
            case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED:
                return "Language not supported";
            case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE:
                return "Language unavailable";
            default:
                return "Didn't understand, please try again.";
        }
    }

    /**
     * Errors that mean this recognizer can't take piped audio at all (as opposed to a bad attempt), when
     * they arrive before it ever said it was ready. Worth one retry with the on-device recognizer.
     */
    static boolean suggestsUnsupportedAudioSource(int code, boolean wasReady) {
        if (wasReady) return false;
        return code == SpeechRecognizer.ERROR_CLIENT
            || code == SpeechRecognizer.ERROR_AUDIO
            || code == SpeechRecognizer.ERROR_SERVER_DISCONNECTED;
    }
}
