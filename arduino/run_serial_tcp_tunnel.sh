#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SCRIPT="$SCRIPT_DIR/serial_tcp_bridge.py"

SERIAL_PORT="${SERIAL_PORT:-}"
BAUD_RATE="${BAUD_RATE:-115200}"
TCP_PORT="${TCP_PORT:-8888}"

usage() {
  cat <<'EOF'
Run Serial -> TCP tunnel for Docker on macOS.

Usage:
  ./arduino/run_serial_tcp_tunnel.sh [options]

Options:
  -p, --port PATH         Serial port, e.g. /dev/cu.usbserial-1240
  -b, --baud-rate RATE    Baud rate (default: 115200)
  -t, --tcp-port PORT     TCP listen port (default: 8888)
  -h, --help              Show this help

You can also use env vars:
  SERIAL_PORT, BAUD_RATE, TCP_PORT
EOF
}

auto_detect_port() {
  local candidates=(
    /dev/cu.usbserial-*
    /dev/cu.usbmodem*
    /dev/cu.wchusbserial*
    /dev/cu.SLAB_USBtoUART*
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if ls $candidate >/dev/null 2>&1; then
      ls $candidate | head -n 1
      return 0
    fi
  done

  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--port)
      SERIAL_PORT="$2"
      shift 2
      ;;
    -b|--baud-rate)
      BAUD_RATE="$2"
      shift 2
      ;;
    -t|--tcp-port)
      TCP_PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$SERIAL_PORT" ]]; then
  if SERIAL_PORT="$(auto_detect_port)"; then
    echo "[tunnel] Auto-detected serial port: $SERIAL_PORT"
  else
    echo "[tunnel] Failed to auto-detect Arduino serial port." >&2
    echo "[tunnel] Available ports:" >&2
    ls -1 /dev/cu.* 2>/dev/null || true
    echo "[tunnel] Pass port manually: --port /dev/cu.usbserial-XXXX" >&2
    exit 1
  fi
fi

if [[ ! -e "$SERIAL_PORT" ]]; then
  echo "[tunnel] Serial port does not exist: $SERIAL_PORT" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[tunnel] python3 not found in PATH" >&2
  exit 1
fi

if [[ ! -f "$BRIDGE_SCRIPT" ]]; then
  echo "[tunnel] Missing bridge script: $BRIDGE_SCRIPT" >&2
  exit 1
fi

echo "[tunnel] Starting Serial -> TCP bridge"
echo "[tunnel] Serial: $SERIAL_PORT"
echo "[tunnel] Baud:   $BAUD_RATE"
echo "[tunnel] TCP:    0.0.0.0:$TCP_PORT"

action_msg="python3 $BRIDGE_SCRIPT --port $SERIAL_PORT --baud-rate $BAUD_RATE --tcp-port $TCP_PORT"
echo "[tunnel] Command: $action_msg"

exec python3 "$BRIDGE_SCRIPT" \
  --port "$SERIAL_PORT" \
  --baud-rate "$BAUD_RATE" \
  --tcp-port "$TCP_PORT"
