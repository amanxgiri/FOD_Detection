from datetime import UTC, datetime

import numpy as np

from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import FramePacket


def make_packet(sequence_id: int) -> FramePacket:
    return FramePacket(
        sequence_id=sequence_id,
        captured_at=datetime.now(UTC),
        frame=np.zeros((4, 4, 3), dtype=np.uint8),
    )


def test_buffer_exposes_latest_frame_only() -> None:
    buffer = LatestFrameBuffer()
    first = make_packet(1)
    second = make_packet(2)

    buffer.publish(first)
    buffer.publish(second)

    assert buffer.get_latest() is second


def test_wait_for_newer_returns_existing_newer_packet() -> None:
    buffer = LatestFrameBuffer()
    packet = make_packet(5)
    buffer.publish(packet)

    assert buffer.wait_for_newer(4, timeout=0.01) is packet


def test_wait_for_newer_times_out_when_no_new_frame() -> None:
    buffer = LatestFrameBuffer()
    buffer.publish(make_packet(5))

    assert buffer.wait_for_newer(5, timeout=0.01) is None
