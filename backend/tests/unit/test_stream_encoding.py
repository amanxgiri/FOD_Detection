from datetime import UTC, datetime, timedelta

import cv2
import numpy as np

from app.api.routes.stream import (
    BOUNDARY,
    annotate_frame_age,
    calculate_frame_age_ms,
    encode_jpeg,
    encode_multipart_frame,
)


def test_encode_jpeg_returns_decodable_image() -> None:
    frame = np.full((20, 30, 3), 128, dtype=np.uint8)

    jpeg = encode_jpeg(frame, jpeg_quality=80)
    decoded = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)

    assert jpeg.startswith(b"\xff\xd8")
    assert decoded is not None
    assert decoded.shape == frame.shape


def test_encode_multipart_frame_wraps_jpeg_payload() -> None:
    frame = np.zeros((20, 30, 3), dtype=np.uint8)

    payload = encode_multipart_frame(frame, jpeg_quality=80)

    assert payload.startswith(f"--{BOUNDARY}\r\n".encode("ascii"))
    assert b"Content-Type: image/jpeg" in payload
    assert b"\xff\xd8" in payload


def test_encode_multipart_frame_adds_visible_frame_age_metadata() -> None:
    frame = np.zeros((80, 320, 3), dtype=np.uint8)
    captured_at = datetime.now(UTC) - timedelta(milliseconds=250)

    payload = encode_multipart_frame(
        frame,
        jpeg_quality=80,
        captured_at=captured_at,
    )

    assert b"X-Frame-Captured-At:" in payload
    assert b"X-Host-Frame-Age-Ms:" in payload


def test_encode_multipart_frame_reports_sensor_to_host_not_stream_age() -> None:
    frame = np.zeros((80, 640, 3), dtype=np.uint8)
    source_captured_at = datetime.now(UTC) - timedelta(milliseconds=300)
    host_captured_at = source_captured_at + timedelta(milliseconds=250)

    payload = encode_multipart_frame(
        frame,
        jpeg_quality=80,
        captured_at=host_captured_at,
        source_captured_at=source_captured_at,
    )

    assert b"X-Sensor-To-Host-Ms: 250.0" in payload
    assert b"X-Sensor-To-Stream-Age-Ms:" not in payload


def test_calculate_frame_age_ms_clamps_clock_skew_to_zero() -> None:
    captured_at = datetime(2026, 1, 1, tzinfo=UTC)

    assert calculate_frame_age_ms(
        captured_at,
        captured_at + timedelta(milliseconds=125),
    ) == 125
    assert calculate_frame_age_ms(
        captured_at,
        captured_at - timedelta(milliseconds=1),
    ) == 0


def test_annotate_frame_age_draws_without_mutating_source() -> None:
    frame = np.zeros((80, 320, 3), dtype=np.uint8)

    annotated = annotate_frame_age(frame, age_ms=125)

    assert np.count_nonzero(frame) == 0
    assert np.count_nonzero(annotated) > 0
