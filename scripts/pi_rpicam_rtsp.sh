#!/usr/bin/env bash
set -euo pipefail

TARGET_IP="${1:-192.168.1.100}"
CAMERA_PATH="${2:-cam3}"
WIDTH="${3:-1280}"
HEIGHT="${4:-720}"
FPS="${5:-30}"
GOP="${6:-15}"

stop_pipeline() {
  jobs -pr | xargs -r kill 2>/dev/null || true
}
trap stop_pipeline EXIT INT TERM

echo "Publishing to rtsp://${TARGET_IP}:8554/${CAMERA_PATH} over TCP"
while true; do
  if ! rpicam-vid \
    -t 0 \
    --width "$WIDTH" \
    --height "$HEIGHT" \
    --framerate "$FPS" \
    --intra "$GOP" \
    --low-latency 1 \
    --codec h264 \
    --inline \
    --libav-format h264 \
    -o - |
    ffmpeg \
      -loglevel warning \
      -fflags nobuffer \
      -f h264 \
      -r "$FPS" \
      -i - \
      -c copy \
      -f rtsp \
      -rtsp_transport tcp \
      -pkt_size 1200 \
      "rtsp://${TARGET_IP}:8554/${CAMERA_PATH}"; then
    echo "Publisher stopped or failed" >&2
  fi
  echo "Publisher stopped; retrying in 2 seconds" >&2
  sleep 2
done
