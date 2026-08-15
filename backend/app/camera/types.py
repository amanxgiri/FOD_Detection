from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray


FrameArray = NDArray[np.uint8]


class CameraStatus(StrEnum):
    NOT_STARTED = "not_started"
    OPENING = "opening"
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    STOPPED = "stopped"


@dataclass(frozen=True)
class FramePacket:
    sequence_id: int
    captured_at: datetime
    frame: FrameArray
    camera_id: str = "camera_1"
    source_captured_at: datetime | None = None
    source_sequence_id: int | None = None
    capture_to_host_ms: float | None = None
