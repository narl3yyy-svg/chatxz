#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Check for virtual env
if [ -n "$VIRTUAL_ENV" ]; then
    PIP="$VIRTUAL_ENV/bin/pip"
    PYTHON="$VIRTUAL_ENV/bin/python"
else
    PIP="pip"
    PYTHON="python3"
fi

install_deps() {
    echo "Installing dependencies..."
    $PIP install --user --break-system-packages rns aiohttp 2>/dev/null || \
    $PIP install rns aiohttp
}

case "${1:-}" in
    install)
        install_deps
        $PIP install --user --break-system-packages -e . 2>/dev/null || $PIP install -e .
        echo "Done. Run ./run.sh web"
        ;;
    web|server)
        install_deps
        PYTHONPATH="$DIR" $PYTHON -m chatxz.web.server "${@:2}"
        ;;
    cli)
        install_deps
        PYTHONPATH="$DIR" $PYTHON -m chatxz.app "${@:2}"
        ;;
    *)
        echo "chatxz - Reticulum Chat"
        echo
        echo "Usage: ./run.sh <command> [args]"
        echo
        echo "Commands:"
        echo "  install          Install dependencies and package"
        echo "  web [--share]    Start web server (http://localhost:8742)"
        echo "  cli [options]    Start CLI mode"
        echo
        echo "Examples:"
        echo "  ./run.sh web"
        echo "  ./run.sh web --share"
        echo "  ./run.sh cli --daemon"
        echo "  ./run.sh cli --connect <hash> --send hello"
        ;;
esac
