#!/usr/bin/env python3
"""Publish a Picamera2 H.264 feed with an in-frame sensor timestamp marker."""

from __future__ import annotations

import argparse
import signal
import socket
import struct
import threading
import time
import zlib
from datetime import UTC, datetime

import numpy as np

try:
    import cv2
except ImportError:  # The binary marker and latency measurement do not require OpenCV.
    cv2 = None


MARKER_MAGIC = b"FD"
MARKER_VERSION = 2
MARKER_COLUMNS = 92
MARKER_ROWS = 2
MARKER_CELL_SIZE = 6
MARKER_RIGHT_MARGIN = 8
MARKER_TOP = 8
MARKER_PAYLOAD_FORMAT = ">2sBIIQ"


def encode_marker(camera_id: str, sequence_id: int, epoch_us: int) -> bytes:
    hostname_identity = zlib.crc32(camera_id.encode("utf-8")) & 0xFFFFFFFF
    body = struct.pack(
        MARKER_PAYLOAD_FORMAT,
        MARKER_MAGIC,
        MARKER_VERSION,
        hostname_identity,
        sequence_id & 0xFFFFFFFF,
        epoch_us,
    )
    return body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def draw_timestamp_marker(
    frame: np.ndarray,
    camera_id: str,
    sequence_id: int,
    epoch_us: int,
    show_text: bool = True,
) -> None:
    marker = encode_marker(camera_id, sequence_id, epoch_us)
    bits = [(byte >> shift) & 1 for byte in marker for shift in range(7, -1, -1)]
    marker_width = MARKER_COLUMNS * MARKER_CELL_SIZE
    left = frame.shape[1] - MARKER_RIGHT_MARGIN - marker_width
    if left < 0 or frame.shape[0] < 60:
        raise ValueError("frame must be at least 560 pixels wide and 60 pixels high")

    marker_pixels = (
        np.asarray(bits, dtype=np.uint8)
        .reshape(MARKER_ROWS, MARKER_COLUMNS)
        .repeat(MARKER_CELL_SIZE, axis=0)
        .repeat(MARKER_CELL_SIZE, axis=1)
        * 255
    )
    marker_height = MARKER_ROWS * MARKER_CELL_SIZE
    marker_region = frame[
        MARKER_TOP : MARKER_TOP + marker_height,
        left : left + marker_width,
    ]
    if marker_region.ndim == 3:
        marker_region[:] = marker_pixels[:, :, None]
    else:
        # YUV420 is represented as a 2-D array. The marker sits entirely in
        # the luma plane, leaving chroma untouched and avoiding RGB conversion.
        marker_region[:] = marker_pixels

    if show_text and cv2 is not None:
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
    parser.add_argument(
        "--camera-id",
        default=socket.gethostname().lower(),
        help="Stable camera identity (default: this Pi hostname)",
    )
    parser.add_argument(
        "--publish-url",
        default=None,
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

    # Picamera2 0.3.31 calls PyAV's newer from_numpy_buffer API, while some
    # Raspberry Pi OS images still ship PyAV 10. Keep the workaround local to
    # Picamera2's software H.264 encoder instead of modifying system packages.
    try:
        import picamera2.encoders.libav_h264_encoder as libav_h264_encoder

        original_av = libav_h264_encoder.av
        if not hasattr(original_av.VideoFrame, "from_numpy_buffer"):
            original_video_frame = original_av.VideoFrame

            class CompatibleVideoFrame:
                @staticmethod
                def from_ndarray(array, format, width=None):
                    del width
                    return original_video_frame.from_ndarray(array, format=format)

                @staticmethod
                def from_numpy_buffer(array, format, width=None):
                    del width
                    return original_video_frame.from_ndarray(array, format=format)

            class CompatibleAvModule:
                VideoFrame = CompatibleVideoFrame

                def __getattr__(self, name):
                    return getattr(original_av, name)

            libav_h264_encoder.av = CompatibleAvModule()
    except ImportError:
        pass

    if args.publish_url is None:
        args.publish_url = f"rtsp://192.168.1.100:8554/{args.camera_id}"
    picam2 = Picamera2(args.camera_index)
    config = picam2.create_video_configuration(
        main={"size": (args.width, args.height), "format": "YUV420"},
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
                args.camera_id,
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
        f"-f rtsp -rtsp_transport tcp -pkt_size 1200 {args.publish_url}",
        audio=False,
    )
    stop_event = threading.Event()

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    print(f"Publishing {args.camera_id} to {args.publish_url}")
    print("The Pi clock must be NTP-synchronized for capture-to-laptop delay to be valid.")
    if cv2 is None and not args.no_readable_timestamp:
        print("OpenCV is unavailable; publishing the machine-readable timestamp marker only.")
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
