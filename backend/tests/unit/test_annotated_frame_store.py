from datetime import UTC, datetime

import numpy as np

from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore


def make_frame(sequence_id: int) -> AnnotatedFrame:
    return AnnotatedFrame(
        sequence_id=sequence_id,
        captured_at=datetime.now(UTC),
        frame=np.zeros((4, 4, 3), dtype=np.uint8),
    )


def test_store_exposes_latest_annotated_frame() -> None:
    store = LatestAnnotatedFrameStore()
    first = make_frame(1)
    second = make_frame(2)

    store.publish(first)
    store.publish(second)

    assert store.get_latest() is second


def test_store_waits_for_newer_frame() -> None:
    store = LatestAnnotatedFrameStore()
    frame = make_frame(3)
    store.publish(frame)

    assert store.wait_for_newer(2, timeout=0.01) is frame
    assert store.wait_for_newer(3, timeout=0.01) is None
