import time

import numpy as np

from app.camera.camera_manager import CameraManager
from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import CameraStatus


class FakeCapture:
    def __init__(self, frames: list[np.ndarray]) -> None:
        self.frames = frames
        self.released = False

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self) -> None:
        self.released = True


def test_capture_one_publishes_timestamped_sequence() -> None:
    frame = np.ones((8, 8, 3), dtype=np.uint8)
    capture = FakeCapture([frame])
    buffer = LatestFrameBuffer()
    manager = CameraManager(
        "0",
        buffer,
        reconnect_delay_seconds=0.01,
        capture_factory=lambda source: capture,
    )

    packet = manager.capture_one()

    assert packet.sequence_id == 1
    assert packet.captured_at.tzinfo is not None
    assert packet.frame.shape == frame.shape
    assert buffer.get_latest() is packet
    assert capture.released is True


def test_manager_start_stop_releases_capture() -> None:
    frames = [np.ones((8, 8, 3), dtype=np.uint8) for _ in range(3)]
    capture = FakeCapture(frames)
    buffer = LatestFrameBuffer()
    manager = CameraManager(
        "0",
        buffer,
        reconnect_delay_seconds=0.01,
        capture_factory=lambda source: capture,
    )

    manager.start()
    packet = buffer.wait_for_newer(0, timeout=1.0)
    manager.stop()

    assert packet is not None
    assert packet.sequence_id >= 1
    assert capture.released is True
    assert manager.is_running() is False
    assert manager.get_status() == CameraStatus.STOPPED


def test_failed_reads_are_counted() -> None:
    capture = FakeCapture([])
    manager = CameraManager(
        "0",
        LatestFrameBuffer(),
        reconnect_delay_seconds=0.01,
        capture_factory=lambda source: capture,
    )

    manager.start()
    time.sleep(0.05)
    manager.stop()

    assert manager.get_read_failures() >= 1
