import numpy as np

from app.detection.types import BoundingBox, Detection
from app.inference.renderer import FrameRenderer, create_placeholder_frame


def test_renderer_draws_annotation_without_mutating_original() -> None:
    frame = np.zeros((40, 60, 3), dtype=np.uint8)
    original = frame.copy()
    detection = Detection(
        class_id=1,
        class_name="Bolt",
        confidence=0.87,
        bbox=BoundingBox(x1=5, y1=8, x2=30, y2=28),
    )

    annotated = FrameRenderer().render(frame, [detection])

    assert np.array_equal(frame, original)
    assert not np.array_equal(annotated, original)
    assert annotated[8, 5].any()


def test_placeholder_frame_has_expected_shape() -> None:
    frame = create_placeholder_frame(width=320, height=180)

    assert frame.shape == (180, 320, 3)
    assert frame.dtype == np.uint8
    assert frame.any()
