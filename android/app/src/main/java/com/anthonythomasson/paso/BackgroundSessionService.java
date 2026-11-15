package com.anthonythomasson.paso;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.drawable.Icon;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import androidx.core.app.ServiceCompat;
import androidx.core.content.ContextCompat;

/**
 * Foreground service that keeps the process (and therefore the WebView running the session) alive
 * while the app is backgrounded or the screen is off. It owns the media-style notification, a
 * partial wake lock and audio focus; all of them live exactly as long as the service.
 */
public class BackgroundSessionService extends android.app.Service {

    static final String CHANNEL_ID = "paso_session";
    static final int NOTIFICATION_ID = 1;
    private static final String ACTION_CONFIGURE = "com.anthonythomasson.paso.action.CONFIGURE";
    private static final String EXTRA_TITLE = "title";
    private static final String EXTRA_TEXT = "text";
    private static final String EXTRA_PAUSED = "paused";
    private static final String EXTRA_MODE = "mode";
    private static final String WAKE_LOCK_TAG = "paso:session";
    /** Safety net so a leaked lock cannot drain the battery forever; refreshed on every update. */
    private static final long WAKE_LOCK_TIMEOUT_MS = 6L * 60 * 60 * 1000;

    private SessionState state = new SessionState(null, null, false);
    /** The session this instance belongs to; only that session may be ended by this instance. */
    private int generation;
    private PowerManager.WakeLock wakeLock;
    private AudioManager audioManager;
    private AudioFocusRequest focusRequest;
    private boolean hasFocus;

    static boolean isActive() {
        return SessionRegistry.isActive();
    }

    /** Starts the service (or refreshes the running one) with the given notification state. */
    static void start(Context context, SessionState state) {
        SessionRegistry.begin();
        ContextCompat.startForegroundService(context, configureIntent(context, state));
    }

    /** Refreshes the notification of the running service. No-op when no session is active. */
    static void update(Context context, String title, String text, boolean paused) {
        if (!SessionRegistry.isActive()) {
            return;
        }
        context.startService(
            new Intent(context, BackgroundSessionService.class)
                .setAction(ACTION_CONFIGURE)
                .putExtra(EXTRA_TITLE, title)
                .putExtra(EXTRA_TEXT, text)
                .putExtra(EXTRA_PAUSED, paused)
        );
    }

    static void stop(Context context) {
        SessionRegistry.end();
        context.stopService(new Intent(context, BackgroundSessionService.class));
    }

    private static Intent configureIntent(Context context, SessionState state) {
        return new Intent(context, BackgroundSessionService.class)
            .setAction(ACTION_CONFIGURE)
            .putExtra(EXTRA_TITLE, state.title())
            .putExtra(EXTRA_TEXT, state.text())
            .putExtra(EXTRA_PAUSED, state.paused())
            .putExtra(EXTRA_MODE, state.mode().wireName());
    }

    @Override
    public void onCreate() {
        super.onCreate();
        generation = SessionRegistry.generation();
        audioManager = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        createChannel();
        acquireWakeLock();
        // Must be called promptly after startForegroundService(), even if stop() races the first intent.
        promoteToForeground();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            return START_NOT_STICKY;
        }
        if (!SessionRegistry.isActive()) {
            // A stale notification button or a late update reached a service nobody asked for.
            endSession();
            return START_NOT_STICKY;
        }
        SessionAction action = SessionAction.fromIntentAction(intent.getAction());
        if (action != null) {
            handleNotificationAction(action);
            return START_NOT_STICKY;
        }
        String title = intent.getStringExtra(EXTRA_TITLE);
        String text = intent.getStringExtra(EXTRA_TEXT);
        boolean paused = intent.getBooleanExtra(EXTRA_PAUSED, false);
        // Only start() names a mode; update() keeps the one the session began with.
        state = intent.hasExtra(EXTRA_MODE)
            ? new SessionState(title, text, paused, SessionMode.fromWireName(intent.getStringExtra(EXTRA_MODE)))
            : state.withContent(title, text, paused);
        if (state.needsWakeLock()) {
            acquireWakeLock();
            // Focus is kept while paused; it is only re-requested when the user resumes.
            requestAudioFocus();
        } else {
            releaseWakeLock();
        }
        promoteToForeground();
        return START_NOT_STICKY;
    }

    private void handleNotificationAction(SessionAction action) {
        if (action.needsResourcesBeforeForwarding()) {
            // The phone may be locked and dozing: get the CPU and audio focus back now, before JS
            // (which will call update(paused=false)) has had a chance to run.
            acquireWakeLock();
            requestAudioFocus();
        }
        SessionEvents.dispatch(action, SessionSource.NOTIFICATION);
        if (action == SessionAction.STOP) {
            // Stop must work even when the WebView is gone and nobody listens.
            endSession();
        }
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // The activity (and its WebView, which runs the session) was swiped away: nothing left to drive.
        giveUp();
        super.onTaskRemoved(rootIntent);
    }

    @Override
    public void onDestroy() {
        abandonAudioFocus();
        releaseWakeLock();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    /**
     * Ends the session because it can no longer run (foreground start refused, task removed): tells JS
     * so it does not keep believing a session is alive, then tears the service down.
     */
    private void giveUp() {
        SessionEvents.dispatch(SessionAction.STOP, null);
        endSession();
    }

    /** Tears the service down; clears the shared flag only if this instance still owns the session. */
    private void endSession() {
        SessionRegistry.endIfCurrent(generation);
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    /** @return false if the system refused and the session was given up. */
    private boolean promoteToForeground() {
        Notification notification = buildNotification();
        boolean micGranted =
            ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        int types = ForegroundTypes.resolve(Build.VERSION.SDK_INT, micGranted, state.mode());
        try {
            ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, types);
            return true;
        } catch (RuntimeException e) {
            // Microphone type can be refused (e.g. started from the background): retry with media only.
            int mediaOnly = ForegroundTypes.resolve(Build.VERSION.SDK_INT, false, state.mode());
            if (mediaOnly != types) {
                try {
                    ServiceCompat.startForeground(this, NOTIFICATION_ID, notification, mediaOnly);
                    return true;
                } catch (RuntimeException ignored) {
                    // fall through to giving up
                }
            }
            giveUp();
            return false;
        }
    }

    private Notification buildNotification() {
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(this, CHANNEL_ID)
            : new Notification.Builder(this).setPriority(Notification.PRIORITY_LOW);

        SessionAction toggle = state.toggleAction();
        boolean resume = toggle == SessionAction.RESUME;
        builder
            .setSmallIcon(R.drawable.ic_stat_session)
            .setContentTitle(state.title())
            .setContentText(state.text())
            .setStyle(new Notification.BigTextStyle().bigText(state.text()))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setShowWhen(false)
            .setCategory(Notification.CATEGORY_TRANSPORT)
            .setVisibility(Notification.VISIBILITY_PUBLIC)
            .setContentIntent(openAppIntent())
            .addAction(
                action(
                    resume ? R.drawable.ic_action_play : R.drawable.ic_action_pause,
                    getString(resume ? R.string.session_action_resume : R.string.session_action_pause),
                    toggle
                )
            )
            .addAction(action(R.drawable.ic_action_skip, getString(R.string.session_action_skip), SessionAction.SKIP))
            .addAction(action(R.drawable.ic_action_stop, getString(R.string.session_action_stop), SessionAction.STOP))
            .setStyle(new Notification.MediaStyle().setShowActionsInCompactView(0, 1, 2));
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            builder.setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE);
        }
        return builder.build();
    }

    private Notification.Action action(int iconRes, String title, SessionAction sessionAction) {
        Intent intent = new Intent(this, BackgroundSessionService.class).setAction(sessionAction.intentAction());
        PendingIntent pending = PendingIntent.getService(
            this,
            sessionAction.ordinal(),
            intent,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );
        return new Notification.Action.Builder(Icon.createWithResource(this, iconRes), title, pending).build();
    }

    private PendingIntent openAppIntent() {
        Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (launch == null) {
            launch = new Intent(this, MainActivity.class);
        }
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(this, 0, launch, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID,
            getString(R.string.session_channel_name),
            NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription(getString(R.string.session_channel_description));
        channel.setShowBadge(false);
        channel.setSound(null, null);
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    private void acquireWakeLock() {
        if (wakeLock == null) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, WAKE_LOCK_TAG);
            wakeLock.setReferenceCounted(false);
        }
        wakeLock.acquire(WAKE_LOCK_TIMEOUT_MS);
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
        wakeLock = null;
    }

    private final AudioManager.OnAudioFocusChangeListener focusListener = focusChange -> {
        SessionAction action = AudioFocusPolicy.actionFor(focusChange);
        if (action != null) {
            hasFocus = false;
            SessionEvents.dispatch(action, SessionSource.AUDIO_FOCUS);
        }
    };

    private void requestAudioFocus() {
        if (hasFocus || audioManager == null) {
            return;
        }
        abandonAudioFocus(); // never leave a stale request registered
        int result;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            AudioAttributes attributes = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build();
            focusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                .setAudioAttributes(attributes)
                .setOnAudioFocusChangeListener(focusListener)
                .build();
            result = audioManager.requestAudioFocus(focusRequest);
        } else {
            result = audioManager.requestAudioFocus(
                focusListener,
                AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN
            );
        }
        hasFocus = result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
    }

    private void abandonAudioFocus() {
        if (audioManager == null) {
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (focusRequest != null) {
                audioManager.abandonAudioFocusRequest(focusRequest);
                focusRequest = null;
            }
        } else {
            audioManager.abandonAudioFocus(focusListener);
        }
        hasFocus = false;
    }
}
