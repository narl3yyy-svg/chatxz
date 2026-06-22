package com.chatxz.android;

import android.app.Application;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class ChatxzApplication extends Application {
    private static ChatxzApplication instance;

    public static ChatxzApplication getInstance() {
        return instance;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
    }
}