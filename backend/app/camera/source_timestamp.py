from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from app.camera.types import FrameArray


MARKER_MAGIC = b"FD"
MARKER_VERSION = 1
MARKER_COLUMNS = 80
MARKER_ROWS = 2
MARKER_CELL_SIZE = 6
MARKER_RIGHT_MARGIN = 8
MARKER_TOP = 8
MARKER_PAYLOAD_FORMAT = ">2sBBIQ"
MARKER_PAYLOAD_SIZE = struct.calcsize(MARKER_PAYLOAD_FORMAT) + 4


@dataclass(frozen=True)
class SourceTimestamp:
    camera_id: str
    sequence_id: int
    captured_at: datetime


def decode_source_timestamp(frame: FrameArray) -> SourceTimestamp | None:
    """Decode the CRC-protected Pi timestamp marker from an already-decoded frame."""
    if frame.ndim < 2:
        return None
    height, width = frame.shape[:2]
    marker_width = MARKER_COLUMNS * MARKER_CELL_SIZE
    marker_height = MARKER_ROWS * MARKER_CELL_SIZE
    left = width - MARKER_RIGHT_MARGIN - marker_width
    if left < 0 or height < MARKER_TOP + marker_height:
        return None

    samples: list[int] = []
    for row in range(MARKER_ROWS):
        y = MARKER_TOP + row * MARKER_CELL_SIZE + MARKER_CELL_SIZE // 2
        for column in range(MARKER_COLUMNS):
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

    if len(encoded) != MARKER_PAYLOAD_SIZE:
        return None
    body, encoded_crc = encoded[:-4], encoded[-4:]
    if zlib.crc32(body) & 0xFFFFFFFF != struct.unpack(">I", encoded_crc)[0]:
        return None

    magic, version, camera_number, sequence_id, epoch_us = struct.unpack(
        MARKER_PAYLOAD_FORMAT, body
    )
    if magic != MARKER_MAGIC or version != MARKER_VERSION:
        return None
    if camera_number not in {1, 2, 3}:
        return None
    try:
        captured_at = datetime.fromtimestamp(epoch_us / 1_000_000, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None
    return SourceTimestamp(
        camera_id=f"camera_{camera_number}",
        sequence_id=sequence_id,
        captured_at=captured_at,
    )
