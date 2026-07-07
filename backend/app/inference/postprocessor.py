from app.detection.types import BoundingBox, Detection
from app.inference.types import RawDetection


class PostProcessor:
    def __init__(self, confidence_threshold: float = 0.25) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        self.confidence_threshold = confidence_threshold

    def process(
        self,
        detections: list[RawDetection],
        frame_width: int,
        frame_height: int,
    ) -> list[Detection]:
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive")

        processed: list[Detection] = []
        for raw in detections:
            if raw.confidence < self.confidence_threshold:
                continue

            x1 = self._clip(round(raw.x1), 0, frame_width)
            y1 = self._clip(round(raw.y1), 0, frame_height)
            x2 = self._clip(round(raw.x2), 0, frame_width)
            y2 = self._clip(round(raw.y2), 0, frame_height)

            if x2 <= x1 or y2 <= y1:
                continue

            processed.append(
                Detection(
                    class_id=raw.class_id,
                    class_name=raw.class_name,
                    confidence=raw.confidence,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )
        return processed

    @staticmethod
    def _clip(value: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, value))
