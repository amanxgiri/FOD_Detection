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
