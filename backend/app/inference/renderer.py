import cv2
import numpy as np

from app.camera.types import FrameArray
from app.detection.types import Detection


class FrameRenderer:
    def __init__(
        self,
        box_color: tuple[int, int, int] = (0, 255, 0),
        text_color: tuple[int, int, int] = (255, 255, 255),
        label_background_color: tuple[int, int, int] = (0, 128, 0),
    ) -> None:
        self.box_color = box_color
        self.text_color = text_color
        self.label_background_color = label_background_color

    def render(self, frame: FrameArray, detections: list[Detection]) -> FrameArray:
        annotated = frame.copy()
        for detection in detections:
            bbox = detection.bbox
            cv2.rectangle(
                annotated,
                (bbox.x1, bbox.y1),
                (bbox.x2, bbox.y2),
                self.box_color,
                thickness=2,
            )
            label = f"{detection.class_name} {detection.confidence:.2f}"
            self._draw_label(annotated, label, bbox.x1, bbox.y1)
        return annotated

    def _draw_label(self, frame: FrameArray, label: str, x: int, y: int) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        (label_width, label_height), baseline = cv2.getTextSize(
            label,
            font,
            font_scale,
            thickness,
        )
        top = max(0, y - label_height - baseline - 4)
        bottom = top + label_height + baseline + 4
        right = min(frame.shape[1] - 1, x + label_width + 6)
        cv2.rectangle(frame, (x, top), (right, bottom), self.label_background_color, -1)
        cv2.putText(
            frame,
            label,
            (x + 3, bottom - baseline - 2),
            font,
            font_scale,
            self.text_color,
            thickness,
            cv2.LINE_AA,
        )


def create_placeholder_frame(
    width: int = 640,
    height: int = 360,
    message: str = "No annotated frame available",
) -> FrameArray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        message,
        (24, height // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (220, 220, 220),
        2,
        cv2.LINE_AA,
    )
    return frame
