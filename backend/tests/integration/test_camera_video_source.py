from pathlib import Path

import cv2
import numpy as np

from app.camera.camera_manager import CameraManager
from app.camera.frame_buffer import LatestFrameBuffer


def create_test_video(path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, 5.0, (32, 24))
    assert writer.isOpened()
    try:
        for value in (20, 80, 140):
            frame = np.full((24, 32, 3), value, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def test_camera_manager_reads_local_video_source(tmp_path: Path) -> None:
    video_path = tmp_path / "test_runway.avi"
    create_test_video(video_path)
    buffer = LatestFrameBuffer()
    manager = CameraManager(str(video_path), buffer, reconnect_delay_seconds=0.01)

    packet = manager.capture_one(open_timeout_seconds=2.0)

    assert packet.sequence_id == 1
    assert packet.captured_at.tzinfo is not None
    assert packet.frame.shape == (24, 32, 3)
    assert buffer.get_latest() is packet
