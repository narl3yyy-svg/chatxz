"""usb4a-compatible USB helpers using Chaquopy's Java bridge."""

from java import jclass

USB_RECIPIENT_DEVICE = 0x00
USB_RECIPIENT_INTERFACE = 0x01
USB_RECIPIENT_ENDPOINT = 0x02
USB_RECIPIENT_OTHER = 0x03

ACTION_USB_PERMISSION = "com.chatxz.android.USB_PERMISSION"


class USBError(IOError):
    pass


def _context():
    Python = jclass("com.chaquo.python.Python")
    return Python.getPlatform().getApplication()


def get_context():
    return _context()


def get_usb_manager():
    Context = jclass("android.content.Context")
    return _context().getSystemService(Context.USB_SERVICE)


def _iter_devices(usb_manager):
    device_map = usb_manager.getDeviceList()
    if device_map is None:
        return
    values = device_map.values()
    if values is None:
        return
    it = values.iterator()
    while it.hasNext():
        yield it.next()


def get_usb_device_list():
    return list(_iter_devices(get_usb_manager()))


def get_usb_device(device_name):
    target = (device_name or "").strip()
    if not target:
        return None
    for usb_device in get_usb_device_list():
        if usb_device and str(usb_device.getDeviceName()) == target:
            return usb_device
    return None


def has_usb_permission(usb_device):
    return bool(get_usb_manager().hasPermission(usb_device))


def request_usb_permission(usb_device):
    UsbSerialHelper = jclass("com.chatxz.android.UsbSerialHelper")
    UsbSerialHelper.requestPermission(str(usb_device.getDeviceName()))


def build_usb_control_request_type(direction, usb_type, recipient):
    return direction | usb_type | recipient


def arraycopy(source, sourcepos, dest, destpos, numelem):
    dest[destpos:destpos + numelem] = source[sourcepos:sourcepos + numelem]