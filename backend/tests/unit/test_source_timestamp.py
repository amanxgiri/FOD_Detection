from datetime import UTC, datetime

import cv2
import numpy as np

from app.camera.source_timestamp import decode_source_timestamp


def _draw_test_marker(
    frame: np.ndarray,
    camera_number: int,
    sequence_id: int,
    epoch_us: int,
) -> None:
    import struct
    import zlib

    body = struct.pack(">2sBBIQ", b"FD", 1, camera_number, sequence_id, epoch_us)
    marker = body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    bits = [(byte >> shift) & 1 for byte in marker for shift in range(7, -1, -1)]
    left = frame.shape[1] - 8 - (80 * 6)
    for index, bit in enumerate(bits):
        row, column = divmod(index, 80)
        x0 = left + column * 6
        y0 = 8 + row * 6
        frame[y0 : y0 + 6, x0 : x0 + 6] = 255 if bit else 0


def test_decodes_crc_checked_timestamp_after_video_compression() -> None:
    frame = np.full((720, 1280, 3), 90, dtype=np.uint8)
    captured_at = datetime(2026, 8, 15, 10, 20, 30, 123456, tzinfo=UTC)
    epoch_us = int(captured_at.timestamp() * 1_000_000)
    _draw_test_marker(frame, camera_number=2, sequence_id=42, epoch_us=epoch_us)

    ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    assert ok
    compressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    decoded = decode_source_timestamp(compressed)

    assert decoded is not None
    assert decoded.camera_id == "camera_2"
    assert decoded.sequence_id == 42
    assert decoded.captured_at == captured_at


def test_rejects_frame_without_marker() -> None:
    frame = np.full((720, 1280, 3), 90, dtype=np.uint8)

    assert decode_source_timestamp(frame) is None


def test_rejects_corrupt_marker() -> None:
    frame = np.full((720, 1280, 3), 90, dtype=np.uint8)
    _draw_test_marker(frame, camera_number=1, sequence_id=7, epoch_us=1_787_000_000_000_000)
    # Flip the centre of bit 1 (a known one-bit in the magic byte 0x46).
    frame[11, frame.shape[1] - 8 - (80 * 6) + 6 + 3] = 0

    assert decode_source_timestamp(frame) is None
