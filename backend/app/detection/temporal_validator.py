from __future__ import annotations

from dataclasses import dataclass, field

from app.detection.types import BoundingBox, Detection


@dataclass(frozen=True)
class TemporalValidationConfig:
    enabled: bool = True
    window_size: int = 5
    required_hits: int = 3
    match_iou: float = 0.30

    def __post_init__(self) -> None:
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")
        if self.required_hits <= 0:
            raise ValueError("required_hits must be positive")
        if self.required_hits > self.window_size:
            raise ValueError("required_hits cannot exceed window_size")
        if not 0.0 <= self.match_iou <= 1.0:
            raise ValueError("match_iou must be between 0.0 and 1.0")


@dataclass
class TemporalCandidate:
    class_id: int
    class_name: str
    latest_detection: Detection
    hits: list[int] = field(default_factory=list)
    confirmed: bool = False


class TemporalValidator:
    def __init__(self, config: TemporalValidationConfig) -> None:
        self.config = config
        self._candidates: list[TemporalCandidate] = []

    @property
    def candidates(self) -> tuple[TemporalCandidate, ...]:
        return tuple(self._candidates)

    def process(
        self,
        detections: list[Detection],
        sequence_id: int,
    ) -> list[Detection]:
        if not self.config.enabled:
            return detections

        self._expire_candidates(sequence_id)
        newly_confirmed: list[Detection] = []
        for detection in detections:
            candidate = self._find_match(detection)
            if candidate is None:
                candidate = TemporalCandidate(
                    class_id=detection.class_id,
                    class_name=detection.class_name,
                    latest_detection=detection,
                    hits=[],
                )
                self._candidates.append(candidate)

            candidate.latest_detection = detection
            if sequence_id not in candidate.hits:
                candidate.hits.append(sequence_id)
            candidate.hits = self._hits_in_window(candidate.hits, sequence_id)

            if (
                not candidate.confirmed
                and len(candidate.hits) >= self.config.required_hits
            ):
                candidate.confirmed = True
                newly_confirmed.append(detection)

        return newly_confirmed

    def _find_match(self, detection: Detection) -> TemporalCandidate | None:
        best_candidate: TemporalCandidate | None = None
        best_iou = 0.0
        for candidate in self._candidates:
            if candidate.class_id != detection.class_id:
                continue
            iou = calculate_iou(candidate.latest_detection.bbox, detection.bbox)
            if iou >= self.config.match_iou and iou > best_iou:
                best_candidate = candidate
                best_iou = iou
        return best_candidate

    def _expire_candidates(self, sequence_id: int) -> None:
        self._candidates = [
            candidate
            for candidate in self._candidates
            if self._hits_in_window(candidate.hits, sequence_id)
        ]
        for candidate in self._candidates:
            candidate.hits = self._hits_in_window(candidate.hits, sequence_id)

    def _hits_in_window(self, hits: list[int], sequence_id: int) -> list[int]:
        oldest_allowed = sequence_id - self.config.window_size + 1
        return [hit for hit in hits if hit >= oldest_allowed]


def calculate_iou(first: BoundingBox, second: BoundingBox) -> float:
    x1 = max(first.x1, second.x1)
    y1 = max(first.y1, second.y1)
    x2 = min(first.x2, second.x2)
    y2 = min(first.y2, second.y2)

    intersection_width = max(0, x2 - x1)
    intersection_height = max(0, y2 - y1)
    intersection_area = intersection_width * intersection_height
    if intersection_area == 0:
        return 0.0

    first_area = (first.x2 - first.x1) * (first.y2 - first.y1)
    second_area = (second.x2 - second.x1) * (second.y2 - second.y1)
    union_area = first_area + second_area - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area
