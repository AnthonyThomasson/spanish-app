package com.anthonythomasson.paso;

/**
 * Decides whether a service update needs startForeground (promote) or only a refreshed notification.
 * Calling startForeground from the background makes Android 14+ refuse the microphone type, and the
 * fallback to media-only would strip it from the already running service, so it is only called when
 * the service is not foreground yet or genuinely needs a type it does not have.
 */
final class ForegroundPromotion {

    private ForegroundPromotion() {}

    static boolean shouldPromote(boolean alreadyForeground, int currentTypes, int desiredTypes) {
        if (!alreadyForeground) {
            return true;
        }
        // Only an addition is worth a startForeground; dropping a type is never done to a running service.
        return (desiredTypes & ~currentTypes) != 0;
    }
}
