#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/data/bridge/pids"
LOG_DIR="$ROOT_DIR/logs"
CONFIG_FILE="${BRIDGES_CONFIG:-$ROOT_DIR/scripts/bridges.conf}"
CONFIG_EXAMPLE="$ROOT_DIR/scripts/bridges.conf.example"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

mkdir -p "$PID_DIR" "$LOG_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  if [[ -f "$CONFIG_EXAMPLE" ]]; then
    cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
    echo "Created $CONFIG_FILE from example."
    echo "Edit device IDs in $CONFIG_FILE and run again."
    exit 1
  fi
  echo "Missing config file: $CONFIG_FILE"
  exit 1
fi

started_count=0
skipped_count=0

while IFS='|' read -r name script_rel device_id serial_port baud_rate api_url api_key extra_args; do
  [[ -z "${name:-}" ]] && continue
  [[ "${name:0:1}" == "#" ]] && continue

  if [[ -z "${script_rel:-}" || -z "${device_id:-}" ]]; then
    echo "Skipping invalid config row (name/script/device_id required): $name"
    skipped_count=$((skipped_count + 1))
    continue
  fi

  if [[ "$device_id" == REPLACE_* ]]; then
    echo "Skipping $name: set real device_id in $CONFIG_FILE"
    skipped_count=$((skipped_count + 1))
    continue
  fi

  script_path="$ROOT_DIR/$script_rel"
  if [[ ! -f "$script_path" ]]; then
    echo "Skipping $name: bridge script not found: $script_path"
    skipped_count=$((skipped_count + 1))
    continue
  fi

  pid_file="$PID_DIR/${name}.pid"
  log_file="$LOG_DIR/bridge_${name}.log"

  if [[ -f "$pid_file" ]]; then
    old_pid="$(cat "$pid_file" || true)"
    if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "$name already running (PID $old_pid)"
      skipped_count=$((skipped_count + 1))
      continue
    fi
    rm -f "$pid_file"
  fi

  baud_rate="${baud_rate:-115200}"
  api_url="${api_url:-http://localhost:8000/api/v1/ingest/http}"
  api_key="${api_key:-your-secret-api-key-change-this}"

  cmd=(
    "$PYTHON_BIN" "$script_path"
    "--device-id" "$device_id"
    "--api-url" "$api_url"
    "--api-key" "$api_key"
    "--baud-rate" "$baud_rate"
  )

  if [[ -n "${serial_port:-}" && "$serial_port" != "-" ]]; then
    cmd+=("--port" "$serial_port")
  fi

  if [[ -n "${extra_args:-}" && "$extra_args" != "-" ]]; then
    # shellcheck disable=SC2206
    extra_tokens=($extra_args)
    cmd+=("${extra_tokens[@]}")
  fi

  nohup "${cmd[@]}" >> "$log_file" 2>&1 &
  new_pid=$!
  echo "$new_pid" > "$pid_file"

  echo "Started $name (PID $new_pid)"
  echo "  script: $script_rel"
  echo "  log: $log_file"
  started_count=$((started_count + 1))
done < "$CONFIG_FILE"

if [[ $started_count -eq 0 ]]; then
  echo "No bridges started. Check $CONFIG_FILE"
  exit 1
fi

echo "Start summary: started=$started_count skipped=$skipped_count"
