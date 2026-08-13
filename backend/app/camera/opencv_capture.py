from __future__ import annotations

import os
from typing import Any


DEFAULT_FFMPEG_CAPTURE_OPTIONS = (
    "rtsp_transport;udp|probesize;32|analyzeduration;0|fflags;nobuffer|"
    "flags;low_delay|reorder_queue_size;0"
)

# OpenCV reads these options when its FFmpeg capture backend opens a source.
# Set a low-latency default before importing cv2 while still allowing an
# operator-provided process environment value to take precedence.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    DEFAULT_FFMPEG_CAPTURE_OPTIONS,
)

import cv2  # noqa: E402  (environment must be configured first)


def configure_ffmpeg_capture_options(options: str) -> None:
    """Set the process-wide FFmpeg capture options before RTSP sessions open."""
    normalized = options.strip()
    if normalized:
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = normalized


def create_opencv_capture(
    source: int | str,
    *,
    open_timeout_ms: int = 5_000,
    read_timeout_ms: int = 1_000,
    buffer_size: int = 1,
    decoder_threads: int = 1,
) -> Any:
    """Open a source with explicit low-latency behavior for RTSP streams."""
    capture = cv2.VideoCapture()
    if _is_rtsp_source(source):
        params = [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            max(1, int(open_timeout_ms)),
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            max(1, int(read_timeout_ms)),
            cv2.CAP_PROP_N_THREADS,
            max(1, int(decoder_threads)),
        ]
        capture.open(source, cv2.CAP_FFMPEG, params)
    else:
        capture.open(source)

    if capture.isOpened():
        # The FFmpeg backend may ignore this property, but drivers/backends that
        # support it will retain at most one decoded frame for the reader.
        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, max(1, int(buffer_size)))
        except Exception:
            # Buffer size support varies by backend and operating system.
            pass
    return capture


def _is_rtsp_source(source: int | str) -> bool:
    return isinstance(source, str) and source.lower().startswith("rtsp://")
