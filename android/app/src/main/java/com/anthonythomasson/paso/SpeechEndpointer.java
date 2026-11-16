package com.anthonythomasson.paso;

/**
 * Decides when to stop feeding microphone audio to the recognizer, from per-frame loudness.
 *
 * The recognizer gets our recording through a pipe, so it can't rely on its own microphone to notice the
 * end of the answer. This endpointer closes the pipe once speech is followed by a pause, when nobody
 * speaks at all, or when the answer runs too long. It is pure so it can be unit tested.
 */
final class SpeechEndpointer {

    enum Verdict {
        CONTINUE,
        /** Speech was heard and has ended (or ran to the maximum length): finalize the result. */
        END_OF_SPEECH,
        /** Nothing loud enough to be speech within the no-speech window. */
        NO_SPEECH,
        /** Every sample so far is exactly zero: Android is silencing the microphone. */
        SILENCED,
    }

    static final int FRAME_MS = 20;
    /** The first frames only measure background noise, so a noisy room isn't taken for speech. */
    static final int CALIBRATION_MS = 200;
    static final int NO_SPEECH_TIMEOUT_MS = 8_000;
    static final int SILENCED_AFTER_MS = 2_000;
    static final int END_SILENCE_MS = 1_200;
    static final int MAX_UTTERANCE_MS = 15_000;
    /** Frames in a row above the threshold before we call it speech (filters clicks). */
    static final int SPEECH_ONSET_FRAMES = 3;
    /** Speech has to be this many times louder than the background noise. */
    static final double NOISE_MULTIPLIER = 2.5;
    /** Absolute floor for the speech threshold, in 16-bit RMS units. */
    static final double MIN_SPEECH_RMS = 350;

    private int elapsedMs;
    private boolean anyNonZero;
    private double noiseFloor = -1;
    private int loudFrames;
    private boolean speaking;
    private int speechStartMs = -1;
    private int quietMs;

    Verdict onFrame(double rms, boolean allZero) {
        elapsedMs += FRAME_MS;
        if (!allZero) anyNonZero = true;
        if (!anyNonZero) {
            return elapsedMs >= SILENCED_AFTER_MS ? Verdict.SILENCED : Verdict.CONTINUE;
        }

        if (elapsedMs <= CALIBRATION_MS) {
            trackNoise(rms);
            return Verdict.CONTINUE;
        }

        boolean loud = rms >= threshold();
        if (!speaking) {
            loudFrames = loud ? loudFrames + 1 : 0;
            if (!loud) trackNoise(rms);
            if (loudFrames >= SPEECH_ONSET_FRAMES) {
                speaking = true;
                speechStartMs = elapsedMs - SPEECH_ONSET_FRAMES * FRAME_MS;
                quietMs = 0;
            } else if (elapsedMs >= NO_SPEECH_TIMEOUT_MS) {
                return Verdict.NO_SPEECH;
            }
            return Verdict.CONTINUE;
        }

        quietMs = loud ? 0 : quietMs + FRAME_MS;
        if (quietMs >= END_SILENCE_MS) return Verdict.END_OF_SPEECH;
        if (elapsedMs - speechStartMs >= MAX_UTTERANCE_MS) return Verdict.END_OF_SPEECH;
        return Verdict.CONTINUE;
    }

    boolean heardSpeech() {
        return speaking;
    }

    double threshold() {
        double floor = noiseFloor < 0 ? 0 : noiseFloor;
        return Math.max(MIN_SPEECH_RMS, floor * NOISE_MULTIPLIER);
    }

    private void trackNoise(double rms) {
        // Follows the background quickly when it gets quieter, slowly when it gets louder.
        if (noiseFloor < 0) {
            noiseFloor = rms;
        } else {
            double rate = rms < noiseFloor ? 0.3 : 0.05;
            noiseFloor += (rms - noiseFloor) * rate;
        }
    }

    /** RMS of 16-bit little-endian PCM samples in {@code buffer[0..length)}. */
    static double rms(byte[] buffer, int length) {
        int samples = length / 2;
        if (samples == 0) return 0;
        double sum = 0;
        for (int i = 0; i < samples; i++) {
            short s = (short) ((buffer[2 * i] & 0xff) | (buffer[2 * i + 1] << 8));
            sum += (double) s * s;
        }
        return Math.sqrt(sum / samples);
    }

    static boolean allZero(byte[] buffer, int length) {
        for (int i = 0; i < length; i++) {
            if (buffer[i] != 0) return false;
        }
        return true;
    }
}
