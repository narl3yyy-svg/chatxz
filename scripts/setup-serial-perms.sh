#!/usr/bin/env bash
# Grant the current user access to USB serial ports (ttyUSB*, ttyACM*, etc.)
set -euo pipefail

if [ "$EUID" -eq 0 ]; then
    echo "Run as your normal user, not root." >&2
    exit 1
fi

account_has_group() {
    id -Gn "$USER" 2>/dev/null | tr ' ' '\n' | grep -qx "$1"
}

added=0
for grp in dialout uucp; do
    if getent group "$grp" >/dev/null 2>&1; then
        if account_has_group "$grp"; then
            echo "Already in group: $grp"
        else
            sudo usermod -aG "$grp" "$USER"
            echo "Added $USER to group: $grp"
            added=1
        fi
    fi
done

UDEV_RULE="$(cd "$(dirname "$0")" && pwd)/udev/99-chatzx-serial.rules"
if [ -f "$UDEV_RULE" ] && [ ! -f /etc/udev/rules.d/99-chatzx-serial.rules ] && [ -t 0 ]; then
    echo ""
    read -r -p "Install udev rule for USB serial permissions? [Y/n]: " udev_opt
    if [[ ! "$udev_opt" =~ ^[Nn]$ ]]; then
        sudo cp "$UDEV_RULE" /etc/udev/rules.d/99-chatzx-serial.rules
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "Installed /etc/udev/rules.d/99-chatzx-serial.rules"
    fi
fi

if [ "$added" -eq 1 ]; then
    echo ""
    echo "Group added. ./run.sh web will use 'sg dialout' until you log out/in."
    echo "Or log out of Ubuntu fully, then serial works in every new session."
else
    echo ""
    echo "Serial groups configured for $USER."
    if account_has_group dialout && ! id -nG | tr ' ' '\n' | grep -qx dialout; then
        echo "Note: dialout is on your account but not this shell — ./run.sh web uses sg dialout automatically."
    fi
fi