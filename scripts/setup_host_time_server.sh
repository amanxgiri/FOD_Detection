#!/usr/bin/env bash
set -euo pipefail

CAMERA_SUBNET="192.168.1.0/24"
CHECK_ONLY=false

usage() {
  cat <<'EOF'
Configure the Ubuntu FOD host as an NTP server for the camera LAN.

Usage:
  sudo ./scripts/setup_host_time_server.sh [--subnet CIDR] [--check-only]
EOF
}

while (($#)); do
  case "$1" in
    --subnet)
      CAMERA_SUBNET="${2:?--subnet requires a CIDR}"
      shift 2
      ;;
    --check-only)
      CHECK_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

show_status() {
  chronyc tracking
  chronyc sources -n
  ss -ulpn | grep -E '(^|[[:space:]])[^[:space:]]*:123[[:space:]]' || true
}

if $CHECK_ONLY; then
  show_status
  exit 0
fi

if ((EUID != 0)); then
  echo "Run this script with sudo." >&2
  exit 1
fi
if ! command -v chronyc >/dev/null 2>&1; then
  echo "Chrony is required. Install it with: sudo apt install chrony" >&2
  exit 1
fi

install -d -m 0755 /etc/chrony/conf.d
cat >/etc/chrony/conf.d/fod-camera-lan.conf <<EOF
# Managed by setup_host_time_server.sh
allow $CAMERA_SUBNET
EOF
systemctl enable --now chrony.service
systemctl restart chrony.service

echo "Ubuntu is serving NTP to $CAMERA_SUBNET."
show_status
