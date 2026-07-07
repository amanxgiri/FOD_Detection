import cv2
import numpy as np

from app.api.routes.stream import BOUNDARY, encode_jpeg, encode_multipart_frame


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
