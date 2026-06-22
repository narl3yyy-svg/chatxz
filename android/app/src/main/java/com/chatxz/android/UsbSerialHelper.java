package com.chatxz.android;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbManager;
import android.os.Build;

public final class UsbSerialHelper {
    public static final String ACTION_USB_PERMISSION = "com.chatxz.android.USB_PERMISSION";

    private UsbSerialHelper() {}

    public static Context appContext() {
        ChatxzApplication app = ChatxzApplication.getInstance();
        if (app == null) {
            throw new IllegalStateException("ChatxzApplication not initialized");
        }
        return app.getApplicationContext();
    }

    public static UsbManager usbManager() {
        return (UsbManager) appContext().getSystemService(Context.USB_SERVICE);
    }

    public static UsbDevice findDevice(String deviceName) {
        if (deviceName == null || deviceName.isEmpty()) {
            return null;
        }
        UsbManager manager = usbManager();
        if (manager == null) {
            return null;
        }
        for (UsbDevice device : manager.getDeviceList().values()) {
            if (device != null && deviceName.equals(device.getDeviceName())) {
                return device;
            }
        }
        return null;
    }

    public static boolean hasPermission(String deviceName) {
        UsbDevice device = findDevice(deviceName);
        if (device == null) {
            return false;
        }
        UsbManager manager = usbManager();
        return manager != null && manager.hasPermission(device);
    }

    public static void requestPermission(String deviceName) {
        UsbDevice device = findDevice(deviceName);
        if (device == null) {
            return;
        }
        UsbManager manager = usbManager();
        if (manager == null) {
            return;
        }
        if (manager.hasPermission(device)) {
            return;
        }
        Context context = appContext();
        Intent intent = new Intent(ACTION_USB_PERMISSION);
        intent.setPackage(context.getPackageName());
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            flags |= PendingIntent.FLAG_MUTABLE;
        }
        PendingIntent pendingIntent = PendingIntent.getBroadcast(context, 0, intent, flags);
        manager.requestPermission(device, pendingIntent);
    }
}