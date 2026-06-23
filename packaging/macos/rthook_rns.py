"""PyInstaller runtime hook — fix RNS.Interfaces before Reticulum loads."""

import importlib
import sys

_INTERFACE_MODULES = (
    "Interface",
    "UDPInterface",
    "AutoInterface",
    "TCPInterface",
    "LocalInterface",
    "SerialInterface",
    "BackboneInterface",
    "KISSInterface",
    "PipeInterface",
    "I2PInterface",
    "RNodeInterface",
    "RNodeMultiInterface",
    "WeaveInterface",
    "AX25KISSInterface",
)

_RNS_CORE_MODULES = (
    "RNS.Transport",
    "RNS.Destination",
    "RNS.Link",
    "RNS.Packet",
    "RNS.Resource",
    "RNS.Identity",
    "RNS.Cryptography",
    "RNS.vendor.configobj",
    "RNS.vendor.platformutils",
)


def _load_interface_modules():
    import RNS.Interfaces as rns_ifaces

    for name in _INTERFACE_MODULES:
        try:
            importlib.import_module(f"RNS.Interfaces.{name}")
        except Exception:
            pass

    if not getattr(rns_ifaces, "__all__", None) or "Interface" not in rns_ifaces.__all__:
        rns_ifaces.__all__ = list(_INTERFACE_MODULES)


def _inject_reticulum_interfaces():
    ret_mod = sys.modules.get("RNS.Reticulum")
    if ret_mod is None:
        return
    if "Interface" in ret_mod.__dict__:
        return
    for name in _INTERFACE_MODULES:
        try:
            setattr(ret_mod, name, importlib.import_module(f"RNS.Interfaces.{name}"))
        except Exception:
            pass


_load_interface_modules()

try:
    importlib.import_module("RNS.Reticulum")
except Exception:
    pass

_inject_reticulum_interfaces()

for _mod in _RNS_CORE_MODULES:
    try:
        importlib.import_module(_mod)
    except Exception:
        pass

_inject_reticulum_interfaces()
