from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import cv2

from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import CameraStatus, FramePacket
from app.core.logging import get_logger

logger = get_logger(__name__)


class CaptureDevice(Protocol):
    def isOpened(self) -> bool:
        ...

    def read(self) -> tuple[bool, Any]:
        ...

    def release(self) -> None:
        ...


CaptureFactory = Callable[[int | str], CaptureDevice]


class CameraManager:
    def __init__(
        self,
        source: int | str,
        frame_buffer: LatestFrameBuffer,
        reconnect_delay_seconds: float = 2.0,
        capture_factory: CaptureFactory | None = None,
    ) -> None:
        self._source = self._normalize_source(source)
        self._frame_buffer = frame_buffer
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self._capture_factory = capture_factory or cv2.VideoCapture

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture: CaptureDevice | None = None
        self._status = CameraStatus.NOT_STARTED
        self._sequence_id = 0
        self._read_failures = 0

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._status = CameraStatus.OPENING
            self._thread = threading.Thread(
                target=self._capture_loop,
                name="camera-capture",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._release_capture()
        with self._lock:
            self._thread = None
            self._status = CameraStatus.STOPPED

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

    def get_status(self) -> CameraStatus:
        with self._lock:
            return self._status

    def get_read_failures(self) -> int:
        with self._lock:
            return self._read_failures

    def capture_one(self, open_timeout_seconds: float = 5.0) -> FramePacket:
        capture = self._open_capture(open_timeout_seconds=open_timeout_seconds)
        try:
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError(f"camera source {self._source!r} did not return a frame")
            return self._publish_frame(frame)
        finally:
            capture.release()

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            capture = self._open_capture()
            with self._lock:
                self._capture = capture
                self._status = CameraStatus.ONLINE

            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    self._record_read_failure()
                    break
                self._publish_frame(frame)

            self._release_capture()
            if not self._stop_event.is_set():
                time.sleep(self._reconnect_delay_seconds)

    def _open_capture(self, open_timeout_seconds: float | None = None) -> CaptureDevice:
        deadline = (
            time.monotonic() + open_timeout_seconds
            if open_timeout_seconds is not None
            else None
        )
        while not self._stop_event.is_set():
            logger.info("camera opening")
            capture = self._capture_factory(self._source)
            if capture.isOpened():
                logger.info("camera opened")
                return capture

            capture.release()
            with self._lock:
                self._status = CameraStatus.OFFLINE
            logger.warning("camera open failed; retrying")
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"camera source {self._source!r} did not open")
            time.sleep(self._reconnect_delay_seconds)

        raise RuntimeError("camera start was cancelled before source opened")

    def _publish_frame(self, frame: Any) -> FramePacket:
        with self._lock:
            self._sequence_id += 1
            sequence_id = self._sequence_id
            self._status = CameraStatus.ONLINE
        packet = FramePacket(
            sequence_id=sequence_id,
            captured_at=datetime.now(UTC),
            frame=frame.copy(),
        )
        self._frame_buffer.publish(packet)
        return packet

    def _record_read_failure(self) -> None:
        with self._lock:
            self._read_failures += 1
            self._status = CameraStatus.DEGRADED
        logger.warning("camera read failed")

    def _release_capture(self) -> None:
        with self._lock:
            capture = self._capture
            self._capture = None
        if capture is not None:
            capture.release()

    @staticmethod
    def _normalize_source(source: int | str) -> int | str:
        if isinstance(source, int):
            return source
        stripped = source.strip()
        if stripped.isdigit():
            return int(stripped)
        return str(Path(stripped))
