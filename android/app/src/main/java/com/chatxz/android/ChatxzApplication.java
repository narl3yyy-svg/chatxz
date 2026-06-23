package com.chatxz.android;

import android.app.Application;
import android.content.Context;
import android.net.wifi.WifiManager;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class ChatxzApplication extends Application {
    private static ChatxzApplication instance;
    private WifiManager.MulticastLock multicastLock;

    public static ChatxzApplication getInstance() {
        return instance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        acquireMulticastLock();
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
    }

    private void acquireMulticastLock() {
        try {
            WifiManager wifi = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wifi != null) {
                multicastLock = wifi.createMulticastLock("chatxz");
                multicastLock.setReferenceCounted(true);
                multicastLock.acquire();
            }
        } catch (Exception ignored) {}
    }
}