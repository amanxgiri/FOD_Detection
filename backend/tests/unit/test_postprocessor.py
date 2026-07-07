from app.inference.postprocessor import PostProcessor
from app.inference.types import RawDetection


def test_postprocessor_filters_low_confidence_detections() -> None:
    processor = PostProcessor(confidence_threshold=0.5)
    detections = [
        RawDetection(1, "Bolt", 0.49, 1, 1, 10, 10),
        RawDetection(2, "Nut", 0.75, 2, 2, 12, 12),
    ]

    processed = processor.process(detections, frame_width=20, frame_height=20)

    assert len(processed) == 1
    assert processed[0].class_name == "Nut"


def test_postprocessor_clips_boxes_to_frame_bounds() -> None:
    processor = PostProcessor(confidence_threshold=0.1)
    detections = [RawDetection(1, "Bolt", 0.9, -5, -2, 25, 30)]

    processed = processor.process(detections, frame_width=20, frame_height=10)

    assert processed[0].bbox.x1 == 0
    assert processed[0].bbox.y1 == 0
    assert processed[0].bbox.x2 == 20
    assert processed[0].bbox.y2 == 10


def test_postprocessor_rejects_zero_area_after_clipping() -> None:
    processor = PostProcessor(confidence_threshold=0.1)
    detections = [RawDetection(1, "Bolt", 0.9, -5, -2, 0, 0)]

    assert processor.process(detections, frame_width=20, frame_height=10) == []
