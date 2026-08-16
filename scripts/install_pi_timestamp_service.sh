#!/usr/bin/env bash
set -euo pipefail

CAMERA_ID="$(hostname | tr '[:upper:]' '[:lower:]')"
PUBLISH_URL=""
MEDIAMTX_HOST="192.168.1.100"
WIDTH=1280
HEIGHT=720
FPS=30
BITRATE=4000000
GOP=15
SERVICE_NAME="fod-timestamp-camera.service"
INSTALL_DIR="/opt/fod-camera"

usage() {
  cat <<'EOF'
Install the timestamped Picamera2 publisher as a systemd service.

Usage:
  sudo ./scripts/install_pi_timestamp_service.sh \
    --camera-id raspberrypi9

Options:
  --camera-id ID       Stable ID (default: lowercase hostname)
  --publish-url URL    Full MediaMTX URL (default: rtsp://HOST:8554/<hostname>)
  --mediamtx-host HOST MediaMTX host used by the default URL
  --width N            Frame width (default: 1280)
  --height N           Frame height (default: 720)
  --fps N              Frame rate (default: 30)
  --bitrate N          H.264 bitrate (default: 4000000)
  --gop N              Keyframe interval (default: 15)
Run setup_pi_clock_sync.sh first. The publisher uses a YUV420 camera stream so
the timestamp marker can be added without the corrupt/choppy RGB conversion
path seen on some Raspberry Pi 5 Picamera2/PyAV combinations.
EOF
}

while (($#)); do
  case "$1" in
    --camera-id) CAMERA_ID="${2:?}"; shift 2 ;;
    --publish-url) PUBLISH_URL="${2:?}"; shift 2 ;;
    --mediamtx-host) MEDIAMTX_HOST="${2:?}"; shift 2 ;;
    --width) WIDTH="${2:?}"; shift 2 ;;
    --height) HEIGHT="${2:?}"; shift 2 ;;
    --fps) FPS="${2:?}"; shift 2 ;;
    --bitrate) BITRATE="${2:?}"; shift 2 ;;
    --gop) GOP="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ ! "$CAMERA_ID" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]]; then
  echo "--camera-id must be a valid lowercase hostname" >&2
  exit 2
fi
if [[ -z "$PUBLISH_URL" ]]; then
  PUBLISH_URL="rtsp://${MEDIAMTX_HOST}:8554/${CAMERA_ID}"
fi
if [[ ! "$PUBLISH_URL" =~ ^rtsp:// ]]; then
  echo "--publish-url must be an rtsp:// URL" >&2
  exit 2
fi
if ((EUID != 0)); then
  echo "Run this script with sudo." >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLISHER_SOURCE="$SCRIPT_DIR/pi_timestamped_rtsp.py"
if [[ ! -f "$PUBLISHER_SOURCE" ]]; then
  echo "pi_timestamped_rtsp.py must be next to this installer." >&2
  exit 1
fi
if ! python3 -c 'import picamera2, numpy' >/dev/null 2>&1; then
  echo "Missing Picamera2 dependencies. Install: sudo apt install python3-picamera2 python3-numpy ffmpeg" >&2
  exit 1
fi
if [[ "$(timedatectl show --property=NTPSynchronized --value)" != "yes" ]]; then
  echo "Clock is not synchronized. Run setup_pi_clock_sync.sh first." >&2
  exit 1
fi

install -d -m 0755 "$INSTALL_DIR"
install -m 0755 "$PUBLISHER_SOURCE" "$INSTALL_DIR/pi_timestamped_rtsp.py"

SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
cat >"$SERVICE_PATH" <<EOF
[Unit]
Description=FOD timestamped Picamera2 RTSP publisher
Wants=network-online.target time-sync.target
After=network-online.target time-sync.target

[Service]
Type=simple
User=${SUDO_USER:-root}
ExecStart=/usr/bin/python3 $INSTALL_DIR/pi_timestamped_rtsp.py --camera-id $CAMERA_ID --publish-url $PUBLISH_URL --width $WIDTH --height $HEIGHT --fps $FPS --bitrate $BITRATE --gop $GOP
Restart=on-failure
RestartSec=2
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

TARGET_USER="${SUDO_USER:-root}"
if [[ "$TARGET_USER" != "root" ]] && command -v crontab >/dev/null 2>&1; then
  CRON_BACKUP="/home/$TARGET_USER/.fod-crontab-backup-$(date +%Y%m%d%H%M%S)"
  if crontab -u "$TARGET_USER" -l >"$CRON_BACKUP" 2>/dev/null; then
    awk '!/stream_rtsp\.sh/' "$CRON_BACKUP" | crontab -u "$TARGET_USER" -
    chown "$TARGET_USER:$TARGET_USER" "$CRON_BACKUP"
    echo "Legacy crontab backed up to $CRON_BACKUP"
  else
    rm -f "$CRON_BACKUP"
  fi
fi

pkill -f 'rpicam-vid.*-t 0' 2>/dev/null || true
pkill -f 'ffmpeg.*-f rtsp.*192\.168\.1\.100:8554/cam' 2>/dev/null || true
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME"
