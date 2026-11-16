package com.anthonythomasson.paso;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import com.anthonythomasson.paso.SpeechEndpointer.Verdict;
import org.junit.Test;

public class SpeechEndpointerTest {

    private static final double NOISE = 80;
    private static final double VOICE = 3000;

    /** Feeds frames of one loudness for {@code ms}; returns the first non-CONTINUE verdict, or CONTINUE. */
    private static Verdict feed(SpeechEndpointer e, double rms, int ms) {
        for (int t = 0; t < ms; t += SpeechEndpointer.FRAME_MS) {
            Verdict v = e.onFrame(rms, false);
            if (v != Verdict.CONTINUE) return v;
        }
        return Verdict.CONTINUE;
    }

    @Test
    public void endsAfterAPauseFollowingSpeech() {
        SpeechEndpointer e = new SpeechEndpointer();
        assertEquals(Verdict.CONTINUE, feed(e, NOISE, 500));
        assertEquals(Verdict.CONTINUE, feed(e, VOICE, 800));
        assertTrue(e.heardSpeech());
        assertEquals(Verdict.CONTINUE, feed(e, NOISE, SpeechEndpointer.END_SILENCE_MS - 100));
        assertEquals(Verdict.END_OF_SPEECH, feed(e, NOISE, 200));
    }

    @Test
    public void shortPausesBetweenWordsDoNotEndTheAnswer() {
        SpeechEndpointer e = new SpeechEndpointer();
        feed(e, NOISE, 300);
        for (int i = 0; i < 5; i++) {
            assertEquals(Verdict.CONTINUE, feed(e, VOICE, 400));
            assertEquals(Verdict.CONTINUE, feed(e, NOISE, 500));
        }
    }

    @Test
    public void reportsNoSpeechWhenNobodyTalks() {
        SpeechEndpointer e = new SpeechEndpointer();
        assertEquals(Verdict.NO_SPEECH, feed(e, NOISE, SpeechEndpointer.NO_SPEECH_TIMEOUT_MS + 100));
        assertFalse(e.heardSpeech());
    }

    @Test
    public void aSingleClickIsNotSpeech() {
        SpeechEndpointer e = new SpeechEndpointer();
        feed(e, NOISE, 300);
        e.onFrame(VOICE, false);
        feed(e, NOISE, 300);
        assertFalse(e.heardSpeech());
    }

    @Test
    public void capsVeryLongAnswers() {
        SpeechEndpointer e = new SpeechEndpointer();
        feed(e, NOISE, 300);
        assertEquals(Verdict.END_OF_SPEECH, feed(e, VOICE, SpeechEndpointer.MAX_UTTERANCE_MS + 200));
    }

    @Test
    public void allZeroAudioMeansTheMicIsSilenced() {
        SpeechEndpointer e = new SpeechEndpointer();
        Verdict v = Verdict.CONTINUE;
        for (int t = 0; t < SpeechEndpointer.SILENCED_AFTER_MS && v == Verdict.CONTINUE; t += SpeechEndpointer.FRAME_MS) {
            v = e.onFrame(0, true);
        }
        assertEquals(Verdict.SILENCED, v);
    }

    @Test
    public void quietRoomThresholdHasAFloor() {
        SpeechEndpointer e = new SpeechEndpointer();
        feed(e, 1, 500);
        assertEquals(SpeechEndpointer.MIN_SPEECH_RMS, e.threshold(), 0.001);
    }

    @Test
    public void noisyRoomRaisesTheThreshold() {
        SpeechEndpointer e = new SpeechEndpointer();
        feed(e, 400, 1000);
        assertTrue(e.threshold() > 900);
        assertEquals(Verdict.CONTINUE, feed(e, 600, 1000)); // a bit louder noise is not speech
        assertFalse(e.heardSpeech());
    }

    @Test
    public void rmsReadsLittleEndianSixteenBitSamples() {
        byte[] pcm = { (byte) 0xe8, 0x03, 0x18, (byte) 0xfc }; // +1000, -1000
        assertEquals(1000, SpeechEndpointer.rms(pcm, 4), 0.001);
        assertTrue(SpeechEndpointer.allZero(new byte[4], 4));
        assertFalse(SpeechEndpointer.allZero(pcm, 4));
    }

    @Test
    public void unsupportedAudioSourceOnlyBeforeTheRecognizerIsReady() {
        assertTrue(RecognizerErrors.suggestsUnsupportedAudioSource(android.speech.SpeechRecognizer.ERROR_CLIENT, false));
        assertFalse(RecognizerErrors.suggestsUnsupportedAudioSource(android.speech.SpeechRecognizer.ERROR_CLIENT, true));
        assertFalse(RecognizerErrors.suggestsUnsupportedAudioSource(android.speech.SpeechRecognizer.ERROR_NO_MATCH, false));
    }
}
