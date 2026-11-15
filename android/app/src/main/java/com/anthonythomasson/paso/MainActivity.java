package com.anthonythomasson.paso;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Local plugins must be registered before super.onCreate() initialises the bridge.
        registerPlugin(BackgroundSessionPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
