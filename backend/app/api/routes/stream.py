from collections.abc import Iterator
from datetime import UTC, datetime
import time

import cv2
from fastapi import APIRouter, Query, Request
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
    return stream_video(request, "camera_1", frame_limit)


def get_annotated_frame_store(
    request: Request,
    camera_id: str = "camera_1",
) -> LatestAnnotatedFrameStore:
    if camera_id not in {"camera_1", "camera_2", "camera_3"}:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"unknown camera: {camera_id}")
    stores = getattr(request.app.state, "annotated_frame_stores", None)
    if not isinstance(stores, dict):
        stores = {
            known_id: LatestAnnotatedFrameStore()
            for known_id in ("camera_1", "camera_2", "camera_3")
        }
        request.app.state.annotated_frame_stores = stores
        request.app.state.annotated_frame_store = stores["camera_1"]
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
        yield encode_multipart_frame(frame.frame, jpeg_quality=jpeg_quality)
        emitted += 1
        if frame_limit is None:
            time.sleep(0.03)


def encode_multipart_frame(frame: FrameArray, jpeg_quality: int) -> bytes:
    jpeg_bytes = encode_jpeg(frame, jpeg_quality=jpeg_quality)
    return (
        f"--{BOUNDARY}\r\n"
        "Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg_bytes)}\r\n"
        "\r\n"
    ).encode("ascii") + jpeg_bytes + b"\r\n"


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
