#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/data/bridge/pids"

if [[ ! -d "$PID_DIR" ]]; then
  echo "No bridge PID directory found: $PID_DIR"
  exit 0
fi

shopt -s nullglob
pid_files=("$PID_DIR"/*.pid)
shopt -u nullglob

if [[ ${#pid_files[@]} -eq 0 ]]; then
  echo "No running bridges found (no pid files)"
  exit 0
fi

stopped_count=0
not_found_count=0
forced_count=0

for pid_file in "${pid_files[@]}"; do
  name="$(basename "$pid_file" .pid)"
  pid="$(cat "$pid_file" || true)"

  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    echo "$name: empty pid file removed"
    not_found_count=$((not_found_count + 1))
    continue
  fi

  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pid_file"
    echo "$name: process $pid not found, pid file removed"
    not_found_count=$((not_found_count + 1))
    continue
  fi

  kill -TERM "$pid"

  stopped=false
  for _ in $(seq 1 20); do
    if kill -0 "$pid" 2>/dev/null; then
      sleep 0.5
    else
      stopped=true
      break
    fi
  done

  if [[ "$stopped" == "true" ]]; then
    rm -f "$pid_file"
    echo "$name: stopped gracefully"
    stopped_count=$((stopped_count + 1))
    continue
  fi

  echo "$name: graceful timeout, forcing kill"
  kill -KILL "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  forced_count=$((forced_count + 1))
done

echo "Stop summary: graceful=$stopped_count forced=$forced_count missing=$not_found_count"
