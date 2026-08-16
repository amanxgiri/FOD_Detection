#!/usr/bin/env bash
set -euo pipefail

TIME_SERVER="192.168.1.100"
WAIT_SECONDS=45
CHECK_ONLY=false

usage() {
  cat <<'EOF'
Configure a Raspberry Pi to synchronize its clock with the FOD backend host.

Usage:
  sudo ./scripts/setup_pi_clock_sync.sh [options]

Options:
  --server IP          NTP server address (default: 192.168.1.100)
  --wait-seconds N     Maximum verification wait (default: 45)
  --check-only         Print synchronization diagnostics without changing files
  -h, --help           Show this help

The script prefers an already-installed Chrony service. Otherwise it configures
systemd-timesyncd, which is included with Raspberry Pi OS. It is safe to rerun.
EOF
}

while (($#)); do
  case "$1" in
    --server)
      TIME_SERVER="${2:?--server requires an IP address}"
      shift 2
      ;;
    --wait-seconds)
      WAIT_SECONDS="${2:?--wait-seconds requires a number}"
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
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$TIME_SERVER" =~ ^[0-9a-fA-F:.]+$ ]]; then
  echo "Invalid time-server address: $TIME_SERVER" >&2
  exit 2
fi
if [[ ! "$WAIT_SECONDS" =~ ^[0-9]+$ ]] || ((WAIT_SECONDS < 1)); then
  echo "--wait-seconds must be a positive integer" >&2
  exit 2
fi

print_common_status() {
  echo "Host: $(hostname)"
  echo "Local UTC: $(date --utc --iso-8601=ns)"
  timedatectl show \
    --property=NTPSynchronized \
    --property=NTP \
    --property=Timezone 2>/dev/null
}

check_chrony() {
  chronyc tracking
  chronyc sources -n
  chronyc tracking | grep -q '^Leap status[[:space:]]*:[[:space:]]*Normal$' &&
    chronyc sources -n | awk -v server="$TIME_SERVER" \
      '$1 ~ /^\^\*/ && $2 == server { found=1 } END { exit !found }'
}

check_timesyncd() {
  timedatectl timesync-status 2>/dev/null || true
  [[ "$(timedatectl show --property=NTPSynchronized --value)" == "yes" ]] &&
    timedatectl timesync-status 2>/dev/null | grep -Fq "Server: $TIME_SERVER"
}

if $CHECK_ONLY; then
  print_common_status
  if command -v chronyc >/dev/null 2>&1 && systemctl is-active --quiet chrony; then
    check_chrony
  else
    check_timesyncd
  fi
  exit $?
fi

if ((EUID != 0)); then
  echo "Run this script with sudo." >&2
  exit 1
fi

if command -v chronyc >/dev/null 2>&1 || systemctl list-unit-files chrony.service --no-legend 2>/dev/null | grep -q chrony; then
  install -d -m 0755 /etc/chrony/conf.d
  cat >/etc/chrony/conf.d/fod-camera-time.conf <<EOF
# Managed by setup_pi_clock_sync.sh
server $TIME_SERVER iburst prefer minpoll 4 maxpoll 6
EOF
  systemctl disable --now systemd-timesyncd.service >/dev/null 2>&1 || true
  systemctl enable --now chrony.service
  systemctl restart chrony.service

  deadline=$((SECONDS + WAIT_SECONDS))
  until check_chrony >/dev/null 2>&1; do
    if ((SECONDS >= deadline)); then
      echo "Chrony did not synchronize within ${WAIT_SECONDS}s." >&2
      chronyc tracking || true
      chronyc sources -n || true
      exit 1
    fi
    sleep 1
  done
  chronyc makestep >/dev/null 2>&1 || true
  echo "Clock synchronized with Chrony."
  print_common_status
  chronyc tracking
  chronyc sources -n
else
  install -d -m 0755 /etc/systemd/timesyncd.conf.d
  cat >/etc/systemd/timesyncd.conf.d/fod-camera-time.conf <<EOF
# Managed by setup_pi_clock_sync.sh
[Time]
NTP=$TIME_SERVER
FallbackNTP=
PollIntervalMinSec=16
PollIntervalMaxSec=64
EOF
  timedatectl set-ntp true
  systemctl enable --now systemd-timesyncd.service
  systemctl restart systemd-timesyncd.service

  deadline=$((SECONDS + WAIT_SECONDS))
  until check_timesyncd >/dev/null 2>&1; do
    if ((SECONDS >= deadline)); then
      echo "systemd-timesyncd did not synchronize within ${WAIT_SECONDS}s." >&2
      timedatectl status || true
      timedatectl timesync-status || true
      exit 1
    fi
    sleep 1
  done
  echo "Clock synchronized with systemd-timesyncd."
  print_common_status
  timedatectl timesync-status
fi
