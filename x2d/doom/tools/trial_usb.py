#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""USB transport for the bounded Doom runner; importing performs no device I/O.

Only claims an already configured interface. No configuration switch, kernel
driver detach, maintenance commands or standalone shell CLI is provided here.
"""
import secrets
import struct
import time

VID, PID, INTERFACE, OUT_EP, IN_EP = 0x2756, 0x0009, 3, 0x04, 0x85
REPLY_HEADER = struct.pack('<HBBB', 9, 5, 8, 0xFC)
FRAME_SIZE = 257
FACTORY_ENABLE_USB_ADB_RUNTIME = (
    "/system/bin/toybox nohup /system/bin/sh -c 'sleep 1;"
    "setprop sys.usb.config none;sleep 1;"
    "setprop sys.usb.config rndis,mass_storage,bulk,acm,adb' >/dev/null 2>&1 &")
FACTORY_RESTORE_USB_NO_ADB_RUNTIME = (
    "/system/bin/toybox nohup /system/bin/sh -c 'sleep 1;"
    "setprop sys.usb.config none;sleep 1;"
    "setprop sys.usb.config rndis,mass_storage,bulk,acm' >/dev/null 2>&1 &")


class UsbFactoryError(Exception):
    """Transport, framing or dependency failure."""


def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xFFFF
    return crc


def request(command, cookie):
    try:
        encoded = command.encode('ascii')
    except UnicodeEncodeError as error:
        raise UsbFactoryError('Command must be ASCII') from error
    if len(encoded) > 231 or b'\0' in encoded:
        raise UsbFactoryError('Command must be at most 231 bytes without NUL')
    payload = bytearray(252)
    struct.pack_into('<III', payload, 0, 65, 0, cookie)
    struct.pack_into('<I', payload, 16, 10)
    payload[20:20 + len(encoded)] = encoded
    struct.pack_into('<I', payload, 12, crc16(payload[16:252]))
    return struct.pack('<HBBB', 10, 8, 5, 0xFC) + payload


def extract_frames(buffer):
    frames = []
    while True:
        start = buffer.find(REPLY_HEADER)
        if start < 0:
            if len(buffer) > 4:
                del buffer[:-4]
            break
        if start:
            del buffer[:start]
        if len(buffer) < FRAME_SIZE:
            break
        frame = bytes(buffer[:FRAME_SIZE])
        if struct.unpack_from('<I', frame, 17)[0] != crc16(frame[21:257]):
            del buffer[0]
            continue
        frames.append(frame)
        del buffer[:FRAME_SIZE]
    return frames


def is_timeout(error):
    return getattr(error, 'errno', None) in (60, 110) or 'timeout' in str(error).lower() or 'timed out' in str(error).lower()


class ExistingInterface:
    def __init__(self):
        self.device = self.util = self.in_ep = self.out_ep = None
        self.claimed = False

    def __enter__(self):
        try:
            import usb.core
            import usb.util
            self.util = usb.util
            devices = list(usb.core.find(find_all=True, idVendor=VID, idProduct=PID))
            if len(devices) != 1:
                raise UsbFactoryError('Expected exactly one connected X2D USB device')
            self.device = devices[0]
            config = self.device.get_active_configuration()
            interface = self.util.find_descriptor(config, bInterfaceNumber=INTERFACE, bAlternateSetting=0)
            if interface is None:
                raise UsbFactoryError('Existing USB interface 3 is unavailable')
            self.util.claim_interface(self.device, INTERFACE)
            self.claimed = True
            self.out_ep = self.util.find_descriptor(interface, bEndpointAddress=OUT_EP)
            self.in_ep = self.util.find_descriptor(interface, bEndpointAddress=IN_EP)
            if self.out_ep is None or self.in_ep is None:
                raise UsbFactoryError('Expected bulk endpoints are unavailable')
            return self
        except Exception as error:
            self.close()
            if isinstance(error, UsbFactoryError):
                raise
            raise UsbFactoryError('Cannot claim existing X2D USB interface: ' + str(error)) from error

    def __exit__(self, *args):
        self.close()

    def close(self):
        device, claimed = self.device, self.claimed
        self.claimed = False
        self.device = self.in_ep = self.out_ep = None
        try:
            if claimed:
                self.util.release_interface(device, INTERFACE)
        finally:
            if device is not None:
                self.util.dispose_resources(device)

    def factory_shell(self, command, capture_ms=15000):
        if self.in_ep is None or self.out_ep is None:
            raise UsbFactoryError('USB interface is not open')
        cookie = secrets.randbits(32) or 1
        packet = request(command, cookie)
        try:
            # Drain stale packets once; never retry execution of a command.
            deadline = time.monotonic() + .05
            while time.monotonic() < deadline:
                try:
                    self.in_ep.read(1024, timeout=max(1, int((deadline-time.monotonic())*1000)))
                except Exception as error:
                    if is_timeout(error):
                        break
                    raise
            if self.out_ep.write(packet, timeout=15000) != len(packet):
                raise UsbFactoryError('Short USB write; command was not retried')
            deadline = time.monotonic() + capture_ms / 1000
            buffer, output, received = bytearray(), [], 0
            while time.monotonic() < deadline:
                try:
                    chunk = bytes(self.in_ep.read(1024, timeout=max(1, int((deadline-time.monotonic())*1000))))
                except Exception as error:
                    if is_timeout(error):
                        continue
                    raise
                received += len(chunk)
                if received > 1024*1024:
                    raise UsbFactoryError('USB response exceeds capture bound')
                buffer.extend(chunk)
                for frame in extract_frames(buffer):
                    cmd, function, reply_cookie = struct.unpack_from('<III', frame, 5)
                    if cmd != 65 or reply_cookie != cookie:
                        continue
                    text = frame[25:].split(b'\0', 1)[0].decode('utf-8', errors='replace')
                    if function == 4:
                        output.append(text)
                    else:
                        status = struct.unpack_from('<I', frame, 21)[0]
                        if status:
                            raise UsbFactoryError('HblShell returned status ' + str(status))
                        return ''.join(output).rstrip('\0')
            raise UsbFactoryError('Timed out waiting for matching USB response')
        except UsbFactoryError:
            raise
        except Exception as error:
            raise UsbFactoryError('USB exchange failed: ' + str(error)) from error
