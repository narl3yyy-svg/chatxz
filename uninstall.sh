#!/bin/bash
# chatxz uninstall script - works on Arch, Ubuntu, and other Linux distros

echo "=== chatxz Uninstaller ==="
echo

# Remove pipx package
if command -v pipx &>/dev/null; then
    echo "[1/3] Removing pipx package..."
    pipx uninstall chatxz 2>/dev/null && echo "  Removed chatxz from pipx" || echo "  chatxz not found in pipx (already removed)"
else
    echo "[1/3] pipx not found, skipping package removal"
fi

# Remove config and data
CONFIG_DIR="$HOME/.config/chatxz"
DATA_DIR="$HOME/.local/share/chatxz"

echo "[2/3] Configuration and data:"
echo "  Config: $CONFIG_DIR"
echo "  Data:   $DATA_DIR"
read -p "  Remove all config and data? (y/N) " -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$CONFIG_DIR" && echo "  Removed config directory"
    rm -rf "$DATA_DIR" && echo "  Removed data directory"
    echo "  All chatxz data removed."
else
    echo "  Kept config and data directories."
fi

# Check for leftover binaries
echo "[3/3] Checking for leftover files..."
LEFTOVER=0
for bin in chatxz chatxz-web; do
    if command -v "$bin" &>/dev/null; then
        echo "  WARNING: $bin still found at $(command -v $bin)"
        LEFTOVER=1
    fi
done
if [ "$LEFTOVER" -eq 0 ]; then
    echo "  No leftover binaries found."
fi

echo
echo "=== Uninstall complete ==="
