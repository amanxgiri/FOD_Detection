from __future__ import annotations

from threading import Condition

from app.camera.types import FramePacket


class LatestFrameBuffer:
    """Thread-safe latest-frame-only buffer."""

    def __init__(self) -> None:
        self._condition = Condition()
        self._latest: FramePacket | None = None

    def publish(self, packet: FramePacket) -> None:
        with self._condition:
            self._latest = packet
            self._condition.notify_all()

    def get_latest(self) -> FramePacket | None:
        with self._condition:
            return self._latest

    def wait_for_newer(
        self,
        last_sequence_id: int,
        timeout: float | None = None,
    ) -> FramePacket | None:
        with self._condition:
            has_newer = self._condition.wait_for(
                lambda: self._latest is not None
                and self._latest.sequence_id > last_sequence_id,
                timeout=timeout,
            )
            if not has_newer:
                return None
            return self._latest
