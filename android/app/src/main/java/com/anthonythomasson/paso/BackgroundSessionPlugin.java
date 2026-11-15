package com.anthonythomasson.paso;

import android.Manifest;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.webkit.WebView;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

/**
 * JS-facing side of the background session: start/update/stop the foreground service and forward
 * notification-button / audio-focus actions back to JS as "action" events.
 *
 * While a session is active it also keeps the WebView running with the activity in the background
 * or the screen off (see {@link #keepWebViewRunning()}).
 */
@CapacitorPlugin(
    name = "BackgroundSession",
    permissions = { @Permission(alias = BackgroundSessionPlugin.NOTIFICATIONS, strings = { Manifest.permission.POST_NOTIFICATIONS }) }
)
public class BackgroundSessionPlugin extends Plugin implements SessionEvents.Listener {

    static final String NOTIFICATIONS = "notifications";
    private static final long[] REASSERT_DELAYS_MS = { 0L, 250L, 1000L };

    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private boolean webViewPrioritySaved;
    private int savedRendererPriority;
    private boolean savedRendererWaived;
    private final AppState appState = new AppState();

    @Override
    public void load() {
        SessionEvents.setListener(this);
    }

    @Override
    protected void handleOnDestroy() {
        SessionEvents.clearListener(this);
        mainHandler.removeCallbacksAndMessages(null);
        // The WebView that drives the session dies with the activity; don't leave an orphaned
        // notification and wake lock behind.
        BackgroundSessionService.stop(getContext());
        super.handleOnDestroy();
    }

    @Override
    public void onAction(SessionAction action, SessionSource source, FocusLoss focusLoss) {
        if (action == SessionAction.STOP) {
            restoreWebViewPriority();
        }
        JSObject event = new JSObject();
        event.put("action", action.wireName());
        if (source != null) {
            event.put("source", source.wireName());
        }
        if (focusLoss != null) {
            event.put("focusChange", focusLoss.focusChange);
            event.put("transient", focusLoss.isTransient());
            event.put("call", focusLoss.call);
        }
        notifyListeners("action", event);
    }

    @PluginMethod
    public void start(PluginCall call) {
        if (Build.VERSION.SDK_INT >= 33 && getPermissionState(NOTIFICATIONS) != PermissionState.GRANTED) {
            // Ask first, but start the service whatever the answer: it still keeps the session alive.
            requestPermissionForAlias(NOTIFICATIONS, call, "onNotificationPermissionResult");
            return;
        }
        startService(call);
    }

    @PermissionCallback
    private void onNotificationPermissionResult(PluginCall call) {
        startService(call);
    }

    private void startService(PluginCall call) {
        SessionState state = new SessionState(
            call.getString("title"),
            call.getString("text"),
            Boolean.TRUE.equals(call.getBoolean("paused", false)),
            SessionMode.fromWireName(call.getString("mode"))
        );
        try {
            BackgroundSessionService.start(getContext(), state);
        } catch (RuntimeException e) {
            SessionRegistry.end();
            call.reject("Could not start the background session: " + e.getMessage());
            return;
        }
        keepWebViewRunning();
        call.resolve();
    }

    @PluginMethod
    public void update(PluginCall call) {
        try {
            BackgroundSessionService.update(
                getContext(),
                call.getString("title"),
                call.getString("text"),
                Boolean.TRUE.equals(call.getBoolean("paused", false))
            );
        } catch (RuntimeException e) {
            // The system killed the service while we were in the background: the session is gone.
            // Tell JS (the STOP event also restores the renderer priority) and reject.
            SessionRegistry.end();
            onAction(SessionAction.STOP, null, null);
            call.reject("Could not update the background session: " + e.getMessage());
            return;
        }
        if (BackgroundSessionService.isActive()) {
            // Cheap and idempotent; covers a screen-off or delayed hide after the post-onPause window.
            mainHandler.post(this::applyKeepRunning);
        }
        call.resolve();
    }

    /** Whether the activity is in the background; JS can't trust document.hidden while a session runs. */
    @PluginMethod
    public void getState(PluginCall call) {
        call.resolve(appStateEvent());
    }

    private JSObject appStateEvent() {
        JSObject state = new JSObject();
        state.put("background", appState.isBackground());
        return state;
    }

    @PluginMethod
    public void stop(PluginCall call) {
        BackgroundSessionService.stop(getContext());
        restoreWebViewPriority();
        call.resolve();
    }

    // ---- Keeping the WebView alive while the activity is not visible -------------------------

    @Override
    protected void handleOnPause() {
        super.handleOnPause();
        appState.onPause();
        notifyListeners(AppState.EVENT, appStateEvent());
        if (BackgroundSessionService.isActive()) {
            keepWebViewRunning();
        }
    }

    @Override
    protected void handleOnResume() {
        super.handleOnResume();
        appState.onResume();
        notifyListeners(AppState.EVENT, appStateEvent());
    }

    @Override
    protected void handleOnStop() {
        super.handleOnStop();
        if (BackgroundSessionService.isActive()) {
            keepWebViewRunning();
        }
    }

    /**
     * Capacitor 8 itself never pauses the WebView on onPause (the "KeepRunning" preference defaults
     * to true), but Chromium's WebView still treats a WebView whose window is no longer visible as a
     * hidden page: timers are throttled to once per second (and far less after a few minutes) and
     * the renderer is deprioritised. That would stall the JS-driven session loop. So while a session
     * is active we (1) ask for an always-important renderer, (2) resume timers, and (3) re-dispatch
     * "window visible" to the WebView after the system reports it hidden. The foreground service and
     * its partial wake lock keep the process and CPU alive; this keeps the page itself running.
     */
    private void keepWebViewRunning() {
        for (long delay : REASSERT_DELAYS_MS) {
            mainHandler.postDelayed(this::applyKeepRunning, delay);
        }
    }

    private void applyKeepRunning() {
        if (!BackgroundSessionService.isActive() || getBridge() == null) {
            return;
        }
        WebView webView = getBridge().getWebView();
        if (webView == null) {
            return;
        }
        if (Build.VERSION.SDK_INT >= 26 && !webViewPrioritySaved) {
            savedRendererPriority = webView.getRendererRequestedPriority();
            savedRendererWaived = webView.getRendererPriorityWaivedWhenNotVisible();
            webViewPrioritySaved = true;
            webView.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, false);
        }
        webView.resumeTimers();
        webView.dispatchWindowVisibilityChanged(View.VISIBLE);
    }

    private void restoreWebViewPriority() {
        mainHandler.post(() -> {
            if (!webViewPrioritySaved || getBridge() == null || getBridge().getWebView() == null) {
                return;
            }
            webViewPrioritySaved = false;
            if (Build.VERSION.SDK_INT >= 26) {
                getBridge().getWebView().setRendererPriorityPolicy(savedRendererPriority, savedRendererWaived);
            }
        });
    }
}
