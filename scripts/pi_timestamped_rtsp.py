#!/usr/bin/env python3
"""Publish a Picamera2 H.264 feed with an in-frame sensor timestamp marker."""

from __future__ import annotations

import argparse
import signal
import struct
import threading
import time
import zlib
from datetime import UTC, datetime

import cv2
import numpy as np


MARKER_MAGIC = b"FD"
MARKER_VERSION = 1
MARKER_COLUMNS = 80
MARKER_ROWS = 2
MARKER_CELL_SIZE = 6
MARKER_RIGHT_MARGIN = 8
MARKER_TOP = 8
MARKER_PAYLOAD_FORMAT = ">2sBBIQ"


def encode_marker(camera_number: int, sequence_id: int, epoch_us: int) -> bytes:
    body = struct.pack(
        MARKER_PAYLOAD_FORMAT,
        MARKER_MAGIC,
        MARKER_VERSION,
        camera_number,
        sequence_id & 0xFFFFFFFF,
        epoch_us,
    )
    return body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def draw_timestamp_marker(
    frame: np.ndarray,
    camera_number: int,
    sequence_id: int,
    epoch_us: int,
    show_text: bool = True,
) -> None:
    marker = encode_marker(camera_number, sequence_id, epoch_us)
    bits = [(byte >> shift) & 1 for byte in marker for shift in range(7, -1, -1)]
    marker_width = MARKER_COLUMNS * MARKER_CELL_SIZE
    left = frame.shape[1] - MARKER_RIGHT_MARGIN - marker_width
    if left < 0 or frame.shape[0] < 60:
        raise ValueError("frame must be at least 488 pixels wide and 60 pixels high")

    for index, bit in enumerate(bits):
        row, column = divmod(index, MARKER_COLUMNS)
        x0 = left + column * MARKER_CELL_SIZE
        y0 = MARKER_TOP + row * MARKER_CELL_SIZE
        value = 255 if bit else 0
        frame[y0 : y0 + MARKER_CELL_SIZE, x0 : x0 + MARKER_CELL_SIZE] = value

    if show_text:
        captured_at = datetime.fromtimestamp(epoch_us / 1_000_000, tz=UTC)
        label = f"PI CAP {captured_at:%H:%M:%S}.{epoch_us % 1_000_000:06d} UTC"
        cv2.putText(
            frame,
            label,
            (left, MARKER_TOP + MARKER_ROWS * MARKER_CELL_SIZE + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish a low-latency Picamera2 RTSP feed with sensor timestamps."
    )
    parser.add_argument("--camera-id", choices=("camera_1", "camera_2", "camera_3"), required=True)
    parser.add_argument(
        "--publish-url",
        required=True,
        help=(
            "RTSP publish endpoint, for example "
            "rtsp://192.168.1.100:8554/cam1"
        ),
    )
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--bitrate", type=int, default=4_000_000)
    parser.add_argument("--gop", type=int, default=15, help="H.264 keyframe interval")
    parser.add_argument("--no-readable-timestamp", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from picamera2 import MappedArray, Picamera2
        from picamera2.encoders import H264Encoder
        from picamera2.outputs import FfmpegOutput
    except ImportError as exc:
        raise SystemExit(
            "Picamera2 is unavailable. Install Raspberry Pi OS packages: "
            "sudo apt install python3-picamera2 python3-opencv ffmpeg"
        ) from exc

    camera_number = int(args.camera_id.rsplit("_", 1)[1])
    picam2 = Picamera2(args.camera_index)
    config = picam2.create_video_configuration(
        main={"size": (args.width, args.height), "format": "RGB888"},
        controls={"FrameRate": args.fps},
        buffer_count=4,
    )
    picam2.configure(config)

    # SensorTimestamp is CLOCK_BOOTTIME nanoseconds sampled at the start of frame.
    # Re-sample its UTC offset for each frame so later NTP clock corrections are
    # reflected without restarting this process.
    def boot_to_epoch_offset_ns() -> int:
        wall_before_ns = time.time_ns()
        boot_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        wall_after_ns = time.time_ns()
        return ((wall_before_ns + wall_after_ns) // 2) - boot_ns

    sequence = 0

    def stamp_request(request) -> None:
        nonlocal sequence
        metadata = request.get_metadata()
        sensor_ns = metadata.get("SensorTimestamp")
        if sensor_ns is None:
            return
        sequence = (sequence + 1) & 0xFFFFFFFF
        epoch_us = (int(sensor_ns) + boot_to_epoch_offset_ns()) // 1_000
        with MappedArray(request, "main") as mapped:
            draw_timestamp_marker(
                mapped.array,
                camera_number,
                sequence,
                epoch_us,
                show_text=not args.no_readable_timestamp,
            )

    picam2.pre_callback = stamp_request
    encoder = H264Encoder(
        bitrate=args.bitrate,
        repeat=True,
        iperiod=args.gop,
    )
    output = FfmpegOutput(
        f"-f rtsp -rtsp_transport tcp {args.publish_url}",
        audio=False,
    )
    stop_event = threading.Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    print(f"Publishing {args.camera_id} to {args.publish_url}")
    print("The Pi clock must be NTP-synchronized for capture-to-laptop delay to be valid.")
    picam2.start_recording(encoder, output)
    try:
        while not stop_event.wait(1.0):
            pass
    finally:
        picam2.stop_recording()
        picam2.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
