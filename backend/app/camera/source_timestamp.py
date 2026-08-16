from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from app.camera.types import FrameArray


MARKER_MAGIC = b"FD"
MARKER_VERSION = 2
MARKER_COLUMNS = 92
MARKER_ROWS = 2
MARKER_CELL_SIZE = 6
MARKER_RIGHT_MARGIN = 8
MARKER_TOP = 8
V1_COLUMNS = 80
V1_PAYLOAD_FORMAT = ">2sBBIQ"
V2_PAYLOAD_FORMAT = ">2sBIIQ"


@dataclass(frozen=True)
class SourceTimestamp:
    camera_id: str
    sequence_id: int
    captured_at: datetime


def decode_source_timestamp(frame: FrameArray) -> SourceTimestamp | None:
    """Decode the CRC-protected Pi timestamp marker from an already-decoded frame."""
    return _decode_version(frame, 2) or _decode_version(frame, 1)


def source_identity_matches(camera_id: str, source_camera_id: str) -> bool:
    if source_camera_id.startswith("hostname:"):
        expected = zlib.crc32(camera_id.encode("utf-8")) & 0xFFFFFFFF
        return source_camera_id == f"hostname:{expected:08x}"
    return source_camera_id == camera_id


def _decode_version(frame: FrameArray, expected_version: int) -> SourceTimestamp | None:
    if frame.ndim < 2:
        return None
    height, width = frame.shape[:2]
    columns = MARKER_COLUMNS if expected_version == 2 else V1_COLUMNS
    marker_width = columns * MARKER_CELL_SIZE
    marker_height = MARKER_ROWS * MARKER_CELL_SIZE
    left = width - MARKER_RIGHT_MARGIN - marker_width
    if left < 0 or height < MARKER_TOP + marker_height:
        return None

    samples: list[int] = []
    for row in range(MARKER_ROWS):
        y = MARKER_TOP + row * MARKER_CELL_SIZE + MARKER_CELL_SIZE // 2
        for column in range(columns):
            x = left + column * MARKER_CELL_SIZE + MARKER_CELL_SIZE // 2
            pixel = frame[y, x]
            samples.append(int(np.mean(pixel)))

    # A fixed black/white marker remains well separated after normal H.264 loss.
    bits = [1 if sample >= 128 else 0 for sample in samples]
    encoded = bytearray()
    for offset in range(0, len(bits), 8):
        value = 0
        for bit in bits[offset : offset + 8]:
            value = (value << 1) | bit
        encoded.append(value)

    body, encoded_crc = encoded[:-4], encoded[-4:]
    if zlib.crc32(body) & 0xFFFFFFFF != struct.unpack(">I", encoded_crc)[0]:
        return None

    try:
        if expected_version == 2:
            magic, version, identity, sequence_id, epoch_us = struct.unpack(
                V2_PAYLOAD_FORMAT, body
            )
            camera_id = f"hostname:{identity:08x}"
        else:
            magic, version, camera_number, sequence_id, epoch_us = struct.unpack(
                V1_PAYLOAD_FORMAT, body
            )
            if camera_number not in {1, 2, 3}:
                return None
            camera_id = f"camera_{camera_number}"
    except struct.error:
        return None
    if magic != MARKER_MAGIC or version != expected_version:
        return None
    try:
        captured_at = datetime.fromtimestamp(epoch_us / 1_000_000, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None
    return SourceTimestamp(
        camera_id=camera_id,
        sequence_id=sequence_id,
        captured_at=captured_at,
    )
