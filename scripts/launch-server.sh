#!/usr/bin/env bash
# Launch chatxz web server with serial port groups (dialout/uucp) when needed.
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
export PYTHONPATH="$DIR"

user_has_group() {
    id -Gn "${USER:?}" 2>/dev/null | tr ' ' '\n' | grep -qx "$1"
}

session_has_group() {
    id -nG 2>/dev/null | tr ' ' '\n' | grep -qx "$1"
}

ensure_serial_groups() {
    local setup="$DIR/scripts/setup-serial-perms.sh"
    if user_has_group dialout || user_has_group uucp; then
        return 0
    fi
    if ! getent group dialout >/dev/null 2>&1 && ! getent group uucp >/dev/null 2>&1; then
        return 0
    fi
    echo "[serial] USB serial needs dialout group membership."
    if [ -x "$setup" ]; then
        bash "$setup" || true
    else
        echo "[serial] Run: sudo usermod -aG dialout $USER"
    fi
}

launch_with_group() {
    local grp="$1"
    shift
    local cmd="cd $(printf '%q' "$DIR") && PYTHONPATH=$(printf '%q' "$DIR") $(printf '%q' "$PYTHON") -m chatxz.web.server"
    local arg
    for arg in "$@"; do
        cmd="$cmd $(printf '%q' "$arg")"
    done
    echo "[serial] Starting with active $grp group (sg $grp)"
    exec sg "$grp" -c "$cmd"
}

main() {
    ensure_serial_groups

    for grp in dialout uucp; do
        if getent group "$grp" >/dev/null 2>&1 \
            && user_has_group "$grp" \
            && ! session_has_group "$grp" \
            && command -v sg >/dev/null 2>&1; then
            launch_with_group "$grp" "$@"
        fi
    done

    exec env PYTHONPATH="$DIR" "$PYTHON" -m chatxz.web.server "$@"
}

main "$@"