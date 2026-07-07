from dataclasses import dataclass


@dataclass(frozen=True)
class RawDetection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("detection coordinates must satisfy x1 <= x2 and y1 <= y2")
