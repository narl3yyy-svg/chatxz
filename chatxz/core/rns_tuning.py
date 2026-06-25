"""chatxz-wide RNS performance tuning (private chatxz network only)."""

import math


CHATXZ_RNS_MTU = 1064  # matches RNS UDPInterface.HW_MTU


def apply_chatxz_rns_tuning():
    """Raise RNS MTU above the 500B default for much faster LAN file transfers."""
    import RNS

    mtu = CHATXZ_RNS_MTU
    RNS.Reticulum.MTU = mtu
    RNS.Reticulum.MDU = mtu - RNS.Reticulum.HEADER_MAXSIZE - RNS.Reticulum.IFAC_MIN_SIZE
    RNS.Packet.MDU = RNS.Reticulum.MDU
    RNS.Resource.SDU = RNS.Packet.MDU
    RNS.Link.MDU = (
        math.floor(
            (
                mtu
                - RNS.Reticulum.IFAC_MIN_SIZE
                - RNS.Reticulum.HEADER_MINSIZE
                - RNS.Identity.TOKEN_OVERHEAD
            )
            / RNS.Identity.AES128_BLOCKSIZE
        )
        * RNS.Identity.AES128_BLOCKSIZE
        - 1
    )