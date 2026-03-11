#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  printf '[INFO] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

err() {
  printf '[ERROR] %s\n' "$1" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Command not found: $1"
    exit 1
  fi
}

run_sudo() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    err "Docker Compose is not available."
    exit 1
  fi
}

set_env_var() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -qE "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

prepare_env_file() {
  local env_file="${ROOT_DIR}/.env"
  local env_example="${ROOT_DIR}/.env.example"

  if [[ ! -f "$env_example" ]]; then
    err "Missing .env.example in project root"
    exit 1
  fi

  if [[ ! -f "$env_file" ]]; then
    cp "$env_example" "$env_file"
    log "Created .env from .env.example"
  else
    log ".env already exists, keeping current values"
  fi

  # Generate secure secrets only if defaults are still present.
  local api_key webhook_secret admin_password mqtt_core_password mqtt_admin_password
  api_key="$(openssl rand -hex 24)"
  webhook_secret="$(openssl rand -hex 32)"
  admin_password="$(openssl rand -hex 12)"
  mqtt_core_password="$(openssl rand -hex 12)"
  mqtt_admin_password="$(openssl rand -hex 12)"

  if grep -q '^API_KEY=your-secret-api-key-change-this$' "$env_file"; then
    set_env_var "API_KEY" "$api_key" "$env_file"
  fi
  if grep -q '^WEBHOOK_SECRET=your-webhook-secret$' "$env_file"; then
    set_env_var "WEBHOOK_SECRET" "$webhook_secret" "$env_file"
  fi
  if grep -q '^ADMIN_PASSWORD=change-this-password$' "$env_file"; then
    set_env_var "ADMIN_PASSWORD" "$admin_password" "$env_file"
  fi
  if grep -q '^MQTT_PASSWORD=change-this-mqtt-password$' "$env_file"; then
    set_env_var "MQTT_PASSWORD" "$mqtt_core_password" "$env_file"
  fi
  if grep -q '^MQTT_IOT_CORE_PASSWORD=change-this-mqtt-password$' "$env_file"; then
    set_env_var "MQTT_IOT_CORE_PASSWORD" "$mqtt_core_password" "$env_file"
  fi
  if grep -q '^MQTT_ADMIN_PASSWORD=change-this-admin-password$' "$env_file"; then
    set_env_var "MQTT_ADMIN_PASSWORD" "$mqtt_admin_password" "$env_file"
  fi

  chmod 600 "$env_file"
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker is already installed"
    return
  fi

  require_cmd curl
  require_cmd gpg

  log "Installing Docker CE and Docker Compose plugin"
  run_sudo apt-get update

  run_sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | run_sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  run_sudo chmod a+r /etc/apt/keyrings/docker.gpg

  local codename
  codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${codename} stable" \
    | run_sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

  run_sudo apt-get update
  run_sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

install_prerequisites() {
  log "Installing system prerequisites"
  run_sudo apt-get update
  run_sudo apt-get install -y ca-certificates curl gnupg lsb-release ufw openssl python3 python3-venv python3-pip
}

install_bridge_python_env() {
  local venv_dir="${ROOT_DIR}/.venv"
  local pip_bin="${venv_dir}/bin/pip"

  if [[ ! -d "$venv_dir" ]]; then
    log "Creating Python virtual environment for bridge scripts"
    python3 -m venv "$venv_dir"
  fi

  log "Installing Python packages for bridge"
  "$pip_bin" install --upgrade pip
  "$pip_bin" install -r "${ROOT_DIR}/requirements.txt" requests
}

bridge_config_ready() {
  local bridge_config="${ROOT_DIR}/scripts/bridges.conf"

  if [[ ! -f "$bridge_config" ]]; then
    cp "${ROOT_DIR}/scripts/bridges.conf.example" "$bridge_config"
    warn "Created scripts/bridges.conf from example. Set device_id values before starting bridge service."
    return 1
  fi

  if grep -q 'REPLACE_' "$bridge_config"; then
    warn "scripts/bridges.conf still contains REPLACE_* placeholders."
    return 1
  fi

  return 0
}

setup_bridge_service() {
  local service_file="/etc/systemd/system/gatewaydemo-bridge.service"

  log "Creating systemd service for background bridge"
  run_sudo tee "$service_file" >/dev/null <<EOF
[Unit]
Description=GatewayDemo Arduino Bridge Host Service
After=network.target docker.service
Wants=network.target docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${ROOT_DIR}
ExecStart=/usr/bin/env bash ${ROOT_DIR}/scripts/start_bridge_host.sh
ExecStop=/usr/bin/env bash ${ROOT_DIR}/scripts/stop_bridge_host.sh
User=${SUDO_USER:-$USER}
Group=${SUDO_USER:-$USER}

[Install]
WantedBy=multi-user.target
EOF

run_sudo systemctl daemon-reload
run_sudo systemctl enable gatewaydemo-bridge.service

if bridge_config_ready; then
    run_sudo systemctl restart gatewaydemo-bridge.service
    log "Bridge service started in background"
  else
    warn "Bridge service enabled but not started until bridges.conf is configured"
  fi
}

ensure_compose_available() {
  if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
    return
  fi

  warn "Docker Compose is missing, trying to install plugin"
  run_sudo apt-get update
  run_sudo apt-get install -y docker-compose-plugin

  if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
    err "Failed to install Docker Compose."
    exit 1
  fi
}

configure_docker_user() {
  if [[ "${EUID}" -ne 0 ]]; then
    if id -nG "$USER" | grep -qw docker; then
      log "User $USER is already in docker group"
    else
      log "Adding $USER to docker group"
      run_sudo usermod -aG docker "$USER"
      warn "Re-login may be required for docker group changes to apply"
    fi
  fi

  run_sudo systemctl enable docker
  run_sudo systemctl restart docker
}

open_firewall_ports() {
  log "Configuring UFW rules"
  run_sudo ufw allow OpenSSH || true
  run_sudo ufw allow 8000/tcp comment 'IoT-Core API and Admin UI'
  run_sudo ufw allow 8001/tcp comment 'Webhook receiver'
  run_sudo ufw allow 1883/tcp comment 'MQTT broker'
  run_sudo ufw allow 9001/tcp comment 'MQTT over WebSocket'

  local ufw_status
  ufw_status="$(run_sudo ufw status | head -n 1 || true)"
  if [[ "$ufw_status" == "Status: inactive" ]]; then
    warn "UFW is inactive. Enabling firewall with default deny incoming policy"
    run_sudo ufw --force default deny incoming
    run_sudo ufw --force default allow outgoing
    run_sudo ufw --force enable
  fi
}

start_stack() {
  log "Creating required directories"
  mkdir -p "${ROOT_DIR}/data" "${ROOT_DIR}/logs" "${ROOT_DIR}/mosquitto/data" "${ROOT_DIR}/mosquitto/log"

  log "Building and starting containers"
  compose_cmd -f "${ROOT_DIR}/docker-compose.yml" up -d --build
}

show_summary() {
  local host_ip
  host_ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  if [[ -z "$host_ip" ]]; then
    host_ip="<SERVER_IP>"
  fi

  printf '\nInstallation completed.\n\n'
  printf 'Accessible endpoints:\n'
  printf '  API and Admin UI:     http://%s:8000\n' "$host_ip"
  printf '  Webhook receiver:     http://%s:8001\n' "$host_ip"
  printf '  MQTT broker:          mqtt://%s:1883\n' "$host_ip"
  printf '  MQTT over WebSocket:  ws://%s:9001\n\n' "$host_ip"

  printf 'Useful commands:\n'
  printf '  docker compose -f %s/docker-compose.yml ps\n' "$ROOT_DIR"
  printf '  docker compose -f %s/docker-compose.yml logs -f\n' "$ROOT_DIR"
  printf '  sudo ufw status numbered\n\n'
}

main() {
  require_cmd awk
  require_cmd sed
  require_cmd grep

  install_prerequisites
  install_docker
  configure_docker_user
  ensure_compose_available
  open_firewall_ports

  require_cmd docker
  prepare_env_file
  install_bridge_python_env
  start_stack
  setup_bridge_service
  show_summary
}

main "$@"
