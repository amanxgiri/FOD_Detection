from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Condition

from app.camera.types import FrameArray


@dataclass(frozen=True)
class AnnotatedFrame:
    sequence_id: int
    captured_at: datetime
    frame: FrameArray


class LatestAnnotatedFrameStore:
    def __init__(self) -> None:
        self._condition = Condition()
        self._latest: AnnotatedFrame | None = None

    def publish(self, frame: AnnotatedFrame) -> None:
        with self._condition:
            self._latest = frame
            self._condition.notify_all()

    def get_latest(self) -> AnnotatedFrame | None:
        with self._condition:
            return self._latest

    def wait_for_newer(
        self,
        last_sequence_id: int,
        timeout: float | None = None,
    ) -> AnnotatedFrame | None:
        with self._condition:
            has_newer = self._condition.wait_for(
                lambda: self._latest is not None
                and self._latest.sequence_id > last_sequence_id,
                timeout=timeout,
            )
            if not has_newer:
                return None
            return self._latest
