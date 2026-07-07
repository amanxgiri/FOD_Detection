from datetime import UTC, datetime

import cv2
import numpy as np
import pytest

from app.storage.evidence_store import EvidenceStore


def test_evidence_store_saves_relative_jpeg_path(tmp_path) -> None:
    store = EvidenceStore(tmp_path)
    timestamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
    frame = np.full((20, 30, 3), 100, dtype=np.uint8)

    relative_path = store.save("DET-20260707-000001", frame, timestamp)
    absolute_path = store.resolve(relative_path)
    decoded = cv2.imread(str(absolute_path))

    assert relative_path == "2026/07/07/DET-20260707-000001.jpg"
    assert absolute_path.exists()
    assert decoded is not None
    assert decoded.shape == frame.shape


def test_evidence_store_rejects_path_escape(tmp_path) -> None:
    store = EvidenceStore(tmp_path)

    with pytest.raises(ValueError, match="escapes"):
        store.resolve("../outside.jpg")
