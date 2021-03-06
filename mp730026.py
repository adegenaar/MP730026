# Based on the uPyM5bLE example code @ https://github.com/lemariva/uPyM5BLE/blob/master/ble_examples/ble_temperature.py
# This code finds and connects to the BLE broadcast from the mp730026 multmeter from Multicomp.
#

import bluetooth
import struct
import time
import micropython
from micropython import const
from ble_advertising import decode_services, decode_name
from mp730026_packet import packet
from display import display

_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
_IRQ_GATTS_WRITE = const(1 << 2)
_IRQ_GATTS_READ_REQUEST = const(1 << 3)
_IRQ_SCAN_RESULT = const(1 << 4)
_IRQ_SCAN_COMPLETE = const(1 << 5)
_IRQ_PERIPHERAL_CONNECT = const(1 << 6)
_IRQ_PERIPHERAL_DISCONNECT = const(1 << 7)
_IRQ_GATTC_SERVICE_RESULT = const(1 << 8)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(1 << 9)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(1 << 10)
_IRQ_GATTC_READ_RESULT = const(1 << 11)
_IRQ_GATTC_WRITE_STATUS = const(1 << 12)
_IRQ_GATTC_NOTIFY = const(1 << 13)
_IRQ_GATTC_INDICATE = const(1 << 14)
_IRQ_ALL = const(0xFFFF)

_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)

# service
_ENV_SENSE_UUID = bluetooth.UUID(0xfff0)
# characteristic
_TEMP_UUID = bluetooth.UUID(0xfff4)
_TEMP_CHAR = (
    _TEMP_UUID,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (_TEMP_CHAR,),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_UNKNOWN = const(0)
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)


class BLEMP730026Central:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(handler=self._irq)

        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Cached value (if we have one)
        self._value = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._value_handle = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            # if adv_type in (_ADV_IND, _ADV_DIRECT_IND, _ADV_SCAN_IND) and _ENV_SENSE_UUID in decode_services(adv_data):
            print('adv_type ({}), services({})'.format(
                adv_type, decode_services(adv_data)))
            # The mukltimeter doesn't appear to advertise it's services in the standard way, so we will look for it by name: 'BDM'
            if 'BDM' == decode_name(adv_data):
                # Found a potential device, remember it and stop scanning.
                self._addr_type = addr_type
                # Note: addr buffer is owned by caller so need to copy it.
                self._addr = bytes(addr)
                self._name = decode_name(adv_data) or "?"
                self._ble.gap_scan(None)

        elif event == _IRQ_SCAN_COMPLETE:
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(
                        self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Connect successful.
            conn_handle, addr_type, addr, = data
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                # self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _, = data
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _ENV_SENSE_UUID:
                self._ble.gattc_discover_characteristics(
                    self._conn_handle, start_handle, end_handle
                )

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == _TEMP_UUID:
                self._value_handle = value_handle
                # We've finished connecting and discovering device, fire the connect callback.
                if self._conn_callback:
                    self._conn_callback()

        elif event == _IRQ_GATTC_READ_RESULT:
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(char_data)
                if self._read_callback:
                    self._read_callback(self._value)
                    self._read_callback = None

        elif event == _IRQ_GATTC_NOTIFY:
            conn_handle, value_handle, notify_data = data
            if conn_handle == self._conn_handle:
                self._update_value(notify_data)
                if self._notify_callback:
                    self._notify_callback(self._value)

    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._conn_handle is not None and self._value_handle is not None

    # Find a device advertising the desired service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        # scan for 10 seconds at full power and duty cycle - if the multimeter is turned on and in range,
        # this should be more than enough time to find it
        self._ble.gap_scan(10000, 30000, 30000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, callback=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        if not self._conn_handle:
            return
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Issues an (asynchronous) read, will invoke callback with data.
    def read(self, callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        self._ble.gattc_read(self._conn_handle, self._value_handle)

    # Sets a callback to be invoked when the device notifies us.
    def on_notify(self, callback):
        self._notify_callback = callback

    def _update_value(self, data):
        self._value = struct.unpack(">HHBB", data)
        return self._value

    def value(self):
        return self._value


def demo():
    disp = display(False, False)
    disp.Clear()

    ble = bluetooth.BLE()
    central = BLEMP730026Central(ble)

    not_found = False

    def on_scan(addr_type, addr, name):
        if addr_type is not None:
            print("Found sensor:", addr_type, addr, name)
            central.connect()
        else:
            nonlocal not_found
            not_found = True
            print("No sensor found.")

    def on_notify(value):
        #print("Notification->{}".format([hex(i) for i in value]))
        p = packet(value)
        #print("Reading [" + p.mode + "]: " + p.value + " " + p.units)
        disp.Update(p.hold, p.rel, p.mode, p.value + " " + p.units)

    central.scan(callback=on_scan)
    central.on_notify(callback=on_notify)

    # Wait for connection...
    while not central.is_connected():
        time.sleep_ms(100)
        if not_found:
            return

    print("Connected")

    # Explicitly issue reads, using "print" as the callback.
    while central.is_connected():
        central.read(callback=print)
        time.sleep_ms(2000)

    print("Disconnected")
    disp.Clear()


if __name__ == "__main__":
    demo()
