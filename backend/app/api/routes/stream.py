from collections.abc import Iterator
from datetime import UTC, datetime
import time

import cv2
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.camera.types import FrameArray
from app.core.config import get_settings
from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore
from app.inference.renderer import create_placeholder_frame

router = APIRouter()
BOUNDARY = "frame"


@router.get("/cameras/{camera_id}/stream")
def stream_video(
    request: Request,
    camera_id: str,
    frame_limit: int | None = Query(default=None, ge=1, include_in_schema=False),
) -> StreamingResponse:
    store = get_annotated_frame_store(request, camera_id)
    settings = get_settings()
    return StreamingResponse(
        iter_mjpeg_frames(
            store=store,
            jpeg_quality=settings.stream_jpeg_quality,
            frame_limit=frame_limit,
        ),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )


@router.get("/stream", include_in_schema=False)
def stream_video_compatibility(
    request: Request,
    frame_limit: int | None = Query(default=None, ge=1, include_in_schema=False),
) -> StreamingResponse:
    stores = getattr(request.app.state, "annotated_frame_stores", {})
    camera_id = next(iter(stores), None)
    if camera_id is None:
        raise HTTPException(status_code=404, detail="no registered cameras")
    return stream_video(request, camera_id, frame_limit)


def get_annotated_frame_store(
    request: Request,
    camera_id: str,
) -> LatestAnnotatedFrameStore:
    stores = getattr(request.app.state, "annotated_frame_stores", None)
    if not isinstance(stores, dict) or camera_id not in stores:
        raise HTTPException(status_code=404, detail=f"unknown camera: {camera_id}")
    return stores[camera_id]


def iter_mjpeg_frames(
    store: LatestAnnotatedFrameStore,
    jpeg_quality: int,
    frame_limit: int | None = None,
    wait_timeout_seconds: float = 0.5,
) -> Iterator[bytes]:
    last_sequence_id = -1
    emitted = 0
    placeholder = AnnotatedFrame(
        sequence_id=0,
        captured_at=datetime.now(UTC),
        frame=create_placeholder_frame(),
    )

    while frame_limit is None or emitted < frame_limit:
        frame = store.wait_for_newer(last_sequence_id, timeout=wait_timeout_seconds)
        if frame is None:
            frame = store.get_latest() or placeholder
        last_sequence_id = frame.sequence_id
        yield encode_multipart_frame(
            frame.frame,
            jpeg_quality=jpeg_quality,
            captured_at=frame.captured_at,
            source_captured_at=frame.source_captured_at,
        )
        emitted += 1
        if frame_limit is None:
            time.sleep(0.03)


def encode_multipart_frame(
    frame: FrameArray,
    jpeg_quality: int,
    captured_at: datetime | None = None,
    source_captured_at: datetime | None = None,
) -> bytes:
    headers = ""
    frame_to_encode = frame
    if captured_at is not None:
        sent_at = datetime.now(UTC)
        age_ms = calculate_frame_age_ms(captured_at, sent_at)
        source_to_host_ms = (
            calculate_frame_age_ms(source_captured_at, captured_at)
            if source_captured_at is not None
            else None
        )
        frame_to_encode = annotate_frame_age(frame, age_ms, source_to_host_ms)
        headers = (
            f"X-Frame-Captured-At: {captured_at.isoformat()}\r\n"
            f"X-Host-Frame-Age-Ms: {age_ms:.1f}\r\n"
        )
        if source_captured_at is not None and source_to_host_ms is not None:
            headers += (
                f"X-Source-Captured-At: {source_captured_at.isoformat()}\r\n"
                f"X-Sensor-To-Host-Ms: {source_to_host_ms:.1f}\r\n"
            )
    jpeg_bytes = encode_jpeg(frame_to_encode, jpeg_quality=jpeg_quality)
    return (
        f"--{BOUNDARY}\r\n"
        "Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg_bytes)}\r\n"
        f"{headers}"
        "\r\n"
    ).encode("ascii") + jpeg_bytes + b"\r\n"


def calculate_frame_age_ms(captured_at: datetime, sent_at: datetime) -> float:
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=UTC)
    return max(0.0, (sent_at - captured_at).total_seconds() * 1000)


def annotate_frame_age(
    frame: FrameArray,
    age_ms: float,
    source_to_host_ms: float | None = None,
) -> FrameArray:
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    label = f"Host frame age at send: {age_ms:.0f} ms"
    if source_to_host_ms is not None:
        label = f"Sensor -> host: {source_to_host_ms:.0f} ms | {label}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.35, min(0.7, width / 900))
    thickness = 1 if font_scale < 0.6 else 2
    (text_width, text_height), baseline = cv2.getTextSize(
        label,
        font,
        font_scale,
        thickness,
    )
    padding = max(4, round(font_scale * 10))
    left = padding
    bottom = max(text_height + padding, height - padding)
    top = max(0, bottom - text_height - (padding * 2))
    right = min(width - 1, left + text_width + (padding * 2))
    cv2.rectangle(annotated, (0, top), (right, height - 1), (10, 18, 24), -1)
    cv2.putText(
        annotated,
        label,
        (left, min(height - baseline - 1, bottom - padding)),
        font,
        font_scale,
        (90, 230, 160),
        thickness,
        cv2.LINE_AA,
    )
    return annotated


def encode_jpeg(frame: FrameArray, jpeg_quality: int) -> bytes:
    quality = max(1, min(100, jpeg_quality))
    ok, encoded = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality],
    )
    if not ok:
        raise RuntimeError("failed to encode annotated frame as JPEG")
    return encoded.tobytes()
