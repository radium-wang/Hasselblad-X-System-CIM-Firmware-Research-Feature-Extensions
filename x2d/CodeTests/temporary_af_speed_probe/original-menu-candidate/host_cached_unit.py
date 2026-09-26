"""仅 Windows/桌面 Qt 6.4.1 的编译单元加载验证，不连接设备。"""
import ctypes
import os
from pathlib import Path
from PySide6.QtCore import QUrl
from shiboken6 import getCppPointer


class CachedUnit(ctypes.Structure):
    _fields_ = [('data', ctypes.c_void_p), ('aot', ctypes.c_void_p), ('unused', ctypes.c_void_p)]


Lookup = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)


class Registration(ctypes.Structure):
    _fields_ = [('version', ctypes.c_int), ('lookup', Lookup)]


class HostCache:
    def __init__(self, path):
        os.environ.pop('QML_DISABLE_DISK_CACHE', None)
        os.environ['QML_DISK_CACHE_PATH'] = str(path.parent / '.stock-host/cache')
        import PySide6
        self.dll = ctypes.CDLL(str(Path(PySide6.__file__).parent / 'Qt6Qml.dll'))
        self.storage = ctypes.create_string_buffer(path.read_bytes())
        self.unit = CachedUnit(ctypes.addressof(self.storage), None, None)
        self.core = ctypes.CDLL(str(Path(PySide6.__file__).parent / 'Qt6Core.dll'))
        self.bridge = ctypes.CDLL(str(path.parent / '.stock-host/cache_bridge.dll'))
        self.url = QUrl.fromLocalFile(str(path.parent / '.stock-host/qml/mainmenu/MainScreen.qml'))
        configure = self.bridge.configure
        configure.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        configure(getattr(self.core, '??8QUrl@@QEBA_NAEBV0@@Z'), getCppPointer(self.url)[0], ctypes.addressof(self.unit))
        self.callback = Lookup(('lookup', self.bridge))
        self.registration = Registration(0, self.callback)
        register = getattr(self.dll, '?qmlregister@QQmlPrivate@@YAHW4RegistrationType@1@PEAX@Z')
        register.argtypes = [ctypes.c_int, ctypes.c_void_p]
        register.restype = ctypes.c_int
        register(6, ctypes.byref(self.registration))

    @property
    def hits(self):
        return self.bridge.hit_count()
