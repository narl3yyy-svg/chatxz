#!/usr/bin/env bash
# Stop chatxz server and release ports 8742 (Rust HTTP), 8744 (RNS IPC), 4242 (RNS UDP).
set -euo pipefail

stop_pids() {
  local sig="$1"
  shift
  local pid
  for pid in "$@"; do
    [ -n "$pid" ] || continue
    kill "-$sig" "$pid" 2>/dev/null || true
  done
}

collect_pids() {
  local port="$1"
  local udp="${2:-0}"
  local pids=""

  if command -v lsof >/dev/null 2>&1; then
    if [ "$udp" = "1" ]; then
      pids="$(lsof -n -P -iUDP:"$port" -t 2>/dev/null || true)"
    else
      pids="$(lsof -n -P -iTCP:"$port" -sTCP:LISTEN -t 2>/dev/null || true)"
    fi
  elif command -v ss >/dev/null 2>&1; then
    local flag="-t"
    [ "$udp" = "1" ] && flag="-u"
    while IFS= read -r line; do
      for token in $line; do
        case "$token" in
          pid=*)
            pids="$pids ${token#pid=}"
            ;;
        esac
      done
    done < <(ss -H -n "$flag" -lp 2>/dev/null | grep ":$port " || true)
  fi
  echo "$pids"
}

wait_ports_free() {
  local timeout="$1"
  shift
  local deadline=$((SECONDS + timeout))
  while [ "$SECONDS" -lt "$deadline" ]; do
    local busy=0
    local port
    for port in "$@"; do
      if [ -n "$(collect_pids "$port" 0)" ]; then
        busy=1
        break
      fi
    done
    [ "$busy" -eq 0 ] && return 0
    sleep 0.2
  done
  return 1
}

# Rust owns the Python child — stop HTTP (8742) first so rnsd gets SIGTERM via Drop.
stop_pids TERM $(collect_pids 8742 0)
for pattern in "target/release/chatxz" "chatxz-server"; do
  pkill -TERM -f "$pattern" 2>/dev/null || true
done

wait_ports_free 5 8742 8744 || true

# Remaining RNS/IPC holders (standalone rnsd or stragglers).
stop_pids TERM $(collect_pids 8744 0)
for port in 4242 8743; do
  stop_pids TERM $(collect_pids "$port" 1)
done

sleep 0.5

for port in 8742 8744; do
  stop_pids KILL $(collect_pids "$port" 0)
done
for port in 4242 8743; do
  stop_pids KILL $(collect_pids "$port" 1)
done

for pattern in "chatxz.rnsd" "chatxz.web.server"; do
  pkill -KILL -f "$pattern" 2>/dev/null || true
done

exit 0