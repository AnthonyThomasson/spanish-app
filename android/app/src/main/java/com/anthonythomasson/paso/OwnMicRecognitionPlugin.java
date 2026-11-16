package com.anthonythomasson.paso;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.ParcelFileDescriptor;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.util.Log;
import androidx.core.content.ContextCompat;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;

/**
 * Speech recognition that records the microphone in this app and pipes the audio to the system
 * recognizer (Android 13+, {@link RecognizerIntent#EXTRA_AUDIO_SOURCE}).
 *
 * The regular SpeechRecognizer opens the microphone inside the recognizer's own app (Google), and
 * Android blocks that while our app is in the background or the screen is off: our foreground service
 * only covers our own process. Recording here, under that service's microphone type, keeps Speak
 * answers listening with the screen off. Rejections use the same messages as
 * {@code @capacitor-community/speech-recognition} (see {@link RecognizerErrors}).
 */
@CapacitorPlugin(name = "OwnMicRecognition")
public class OwnMicRecognitionPlugin extends Plugin {

    private static final String TAG = "PasoOwnMic";
    private static final int SAMPLE_RATE = 16_000;
    private static final int FRAME_BYTES = SAMPLE_RATE / 1000 * SpeechEndpointer.FRAME_MS * 2;
    /** How long the recognizer gets to answer once we've stopped sending audio. */
    private static final long RESULT_TIMEOUT_MS = 10_000;

    private final Handler main = new Handler(Looper.getMainLooper());
    /** Main thread only. */
    private Attempt current;
    /** Set once the default recognizer turns out not to accept piped audio. */
    private static volatile boolean preferOnDevice;

    @PluginMethod
    public void isSupported(PluginCall call) {
        JSObject result = new JSObject();
        result.put("supported", Build.VERSION.SDK_INT >= 33 && (defaultAvailable() || onDeviceAvailable()));
        call.resolve(result);
    }

    @PluginMethod
    public void listen(PluginCall call) {
        if (Build.VERSION.SDK_INT < 33) {
            call.reject("Client side error: piped audio needs Android 13");
            return;
        }
        if (ContextCompat.checkSelfPermission(getContext(), Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            call.reject("Insufficient permissions");
            return;
        }
        String language = call.getString("language", "en-US");
        int maxResults = call.getInt("maxResults", 5);
        main.post(() -> {
            if (current != null) current.fail(RecognizerErrors.ABORTED);
            boolean onDevice = (preferOnDevice || !defaultAvailable()) && onDeviceAvailable();
            current = new Attempt(call, language, maxResults, onDevice, false);
            current.start();
        });
    }

    @PluginMethod
    public void stop(PluginCall call) {
        main.post(() -> {
            if (current != null) current.fail(RecognizerErrors.ABORTED);
        });
        call.resolve();
    }

    @Override
    protected void handleOnDestroy() {
        main.post(() -> {
            if (current != null) current.fail(RecognizerErrors.ABORTED);
        });
        super.handleOnDestroy();
    }

    private boolean defaultAvailable() {
        return SpeechRecognizer.isRecognitionAvailable(getContext());
    }

    private boolean onDeviceAvailable() {
        return Build.VERSION.SDK_INT >= 31 && SpeechRecognizer.isOnDeviceRecognitionAvailable(getContext());
    }

    /** One listen: a recording thread writing into a pipe, and a recognizer reading from it. */
    private final class Attempt implements RecognitionListener {

        private final PluginCall call;
        private final String language;
        private final int maxResults;
        private final boolean onDevice;
        private final boolean isRetry;

        private SpeechRecognizer recognizer;
        private AudioRecord record;
        private ParcelFileDescriptor readFd;
        private ParcelFileDescriptor writeFd;
        private volatile boolean capturing;
        // Diagnostics, written by the recording thread and read on the main thread when the attempt ends.
        private final long startedAt = System.currentTimeMillis();
        private volatile double peakRms;
        private volatile double lastThreshold;
        private volatile boolean heardSpeech;
        private volatile String captureEnd = "running";
        private volatile long bytesSent;
        private volatile boolean recognizerStoppedReading;
        private int recognizerError = -1;
        private boolean ready;
        private boolean finished;
        private final Runnable resultTimeout = () -> fail(RecognizerErrors.TIMEOUT);

        Attempt(PluginCall call, String language, int maxResults, boolean onDevice, boolean isRetry) {
            this.call = call;
            this.language = language;
            this.maxResults = maxResults;
            this.onDevice = onDevice;
            this.isRetry = isRetry;
        }

        void start() {
            Context context = getContext();
            try {
                ParcelFileDescriptor[] pipe = ParcelFileDescriptor.createPipe();
                readFd = pipe[0];
                writeFd = pipe[1];

                int minBuffer = AudioRecord.getMinBufferSize(SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
                record = new AudioRecord(
                    MediaRecorder.AudioSource.VOICE_RECOGNITION,
                    SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    Math.max(minBuffer, FRAME_BYTES * 25)
                );
                if (record.getState() != AudioRecord.STATE_INITIALIZED) {
                    fail(RecognizerErrors.RECORDING_FAILED);
                    return;
                }

                recognizer = onDevice
                    ? SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
                    : SpeechRecognizer.createSpeechRecognizer(context);
                recognizer.setRecognitionListener(this);

                // Record first so the start of the answer isn't lost while the recognizer connects;
                // the pipe buffers a couple of seconds.
                record.startRecording();
                if (record.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING) {
                    fail(RecognizerErrors.RECORDING_FAILED);
                    return;
                }
                capturing = true;
                Thread thread = new Thread(this::capture, "paso-own-mic");
                thread.start();

                Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, language);
                intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, maxResults);
                intent.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.getPackageName());
                intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE, readFd);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_CHANNEL_COUNT, 1);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_ENCODING, AudioFormat.ENCODING_PCM_16BIT);
                intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_SAMPLING_RATE, SAMPLE_RATE);
                recognizer.startListening(intent);
                Log.i(TAG, "listening (" + (onDevice ? "on-device" : "default") + " recognizer, " + language + ")");
            } catch (SecurityException e) {
                fail("Insufficient permissions");
            } catch (IOException | RuntimeException e) {
                Log.w(TAG, "could not start", e);
                fail(RecognizerErrors.RECORDING_FAILED + ": " + e.getMessage());
            }
        }

        /** Recording thread: feeds the pipe until the endpointer or the recognizer says stop. */
        private void capture() {
            SpeechEndpointer endpointer = new SpeechEndpointer();
            SpeechEndpointer.Verdict verdict = SpeechEndpointer.Verdict.CONTINUE;
            boolean readFailed = false;
            byte[] frame = new byte[FRAME_BYTES];
            AudioRecord rec = record;
            try (OutputStream out = new FileOutputStream(writeFd.getFileDescriptor())) {
                while (capturing) {
                    int n = rec.read(frame, 0, frame.length);
                    if (n <= 0) {
                        readFailed = capturing;
                        break;
                    }
                    try {
                        out.write(frame, 0, n);
                        bytesSent += n;
                    } catch (IOException e) {
                        recognizerStoppedReading = true;
                        break; // the recognizer closed its end; its own callback reports why
                    }
                    double rms = SpeechEndpointer.rms(frame, n);
                    peakRms = Math.max(peakRms, rms);
                    verdict = endpointer.onFrame(rms, SpeechEndpointer.allZero(frame, n));
                    lastThreshold = endpointer.threshold();
                    heardSpeech = endpointer.heardSpeech();
                    if (verdict != SpeechEndpointer.Verdict.CONTINUE) break;
                }
            } catch (IOException ignored) {
                // closing the stream
            } finally {
                try {
                    rec.stop();
                } catch (IllegalStateException ignored) {}
                rec.release();
                closeQuietly(writeFd); // end of audio for the recognizer
            }
            captureEnd = verdict.name().toLowerCase();
            Log.i(TAG, "capture ended: " + verdict + (readFailed ? " (read failed)" : "") + ", heard speech: " + endpointer.heardSpeech());
            final SpeechEndpointer.Verdict ended = verdict;
            final boolean failedRead = readFailed;
            main.post(() -> onCaptureEnded(ended, failedRead));
        }

        private void onCaptureEnded(SpeechEndpointer.Verdict verdict, boolean readFailed) {
            if (finished) return;
            if (readFailed) {
                fail(RecognizerErrors.RECORDING_FAILED);
                return;
            }
            switch (verdict) {
                case SILENCED:
                    fail(RecognizerErrors.MIC_SILENCED);
                    return;
                default:
                    // End of speech, no speech heard, or the recognizer stopped reading: the recognizer has the
                    // last word (our loudness check may simply have missed a quiet voice).
                    try {
                        recognizer.stopListening();
                    } catch (RuntimeException ignored) {}
                    main.postDelayed(resultTimeout, RESULT_TIMEOUT_MS);
            }
        }

        void fail(String message) {
            if (finished) return;
            Log.i(TAG, "failed: " + message);
            finish();
            reportDiagnostic("failed: " + message);
            call.reject(message);
        }

        /** One line for the screen saying what this attempt saw; temporary, to debug recognition on real phones. */
        private void reportDiagnostic(String outcome) {
            String text = String.format(
                java.util.Locale.US,
                "%s recognizer%s · peak %.0f (speech above %.0f) · speech %s · audio ended: %s%s · %.1f KB sent in %.1f s · %s",
                onDevice ? "on-device" : "default",
                ready ? "" : " (never ready)",
                peakRms,
                lastThreshold,
                heardSpeech ? "yes" : "no",
                captureEnd,
                recognizerStoppedReading ? " (recognizer stopped reading)" : "",
                bytesSent / 1024.0,
                (System.currentTimeMillis() - startedAt) / 1000.0,
                recognizerError >= 0 ? outcome + " (error " + recognizerError + ")" : outcome
            );
            Log.i(TAG, text);
            JSObject event = new JSObject();
            event.put("text", text);
            notifyListeners("diagnostic", event);
        }

        private void finish() {
            finished = true;
            capturing = false;
            main.removeCallbacks(resultTimeout);
            if (record != null) {
                try {
                    record.stop(); // unblocks the recording thread, which releases it
                } catch (IllegalStateException ignored) {}
            }
            if (recognizer != null) {
                try {
                    recognizer.cancel();
                } catch (RuntimeException ignored) {}
                recognizer.destroy();
                recognizer = null;
            }
            closeQuietly(readFd);
            if (current == this) current = null;
        }

        // ---- RecognitionListener (main thread) ----------------------------------------------

        @Override
        public void onReadyForSpeech(Bundle params) {
            ready = true;
        }

        @Override
        public void onResults(Bundle results) {
            if (finished) return;
            ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            Log.i(TAG, "results: " + matches);
            finish();
            reportDiagnostic("heard " + (matches == null || matches.isEmpty() ? "nothing" : "\"" + matches.get(0) + "\""));
            JSObject ret = new JSObject();
            ret.put("matches", new JSArray(matches == null ? new ArrayList<String>() : matches));
            call.resolve(ret);
        }

        @Override
        public void onError(int error) {
            if (finished) return;
            Log.i(TAG, "recognizer error " + error + " (ready: " + ready + ", on-device: " + onDevice + ")");
            recognizerError = error;
            if (!onDevice && !isRetry && RecognizerErrors.suggestsUnsupportedAudioSource(error, ready) && onDeviceAvailable()) {
                Log.i(TAG, "default recognizer refused piped audio; switching to on-device");
                preferOnDevice = true;
                finish();
                current = new Attempt(call, language, maxResults, true, true);
                current.start();
                return;
            }
            fail(RecognizerErrors.text(error));
        }

        @Override
        public void onBeginningOfSpeech() {}

        @Override
        public void onRmsChanged(float rmsdB) {}

        @Override
        public void onBufferReceived(byte[] buffer) {}

        @Override
        public void onEndOfSpeech() {}

        @Override
        public void onPartialResults(Bundle partialResults) {}

        @Override
        public void onEvent(int eventType, Bundle params) {}
    }

    private static void closeQuietly(ParcelFileDescriptor fd) {
        if (fd == null) return;
        try {
            fd.close();
        } catch (IOException ignored) {}
    }
}
