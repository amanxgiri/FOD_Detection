import os

from app.camera import opencv_capture


class FakeVideoCapture:
    def __init__(self) -> None:
        self.open_args: tuple | None = None
        self.set_calls: list[tuple[int, int]] = []

    def open(self, *args) -> bool:
        self.open_args = args
        return True

    def isOpened(self) -> bool:
        return True

    def set(self, property_id: int, value: int) -> bool:
        self.set_calls.append((property_id, value))
        return True


def test_rtsp_capture_forces_ffmpeg_timeouts_and_minimal_buffer(monkeypatch) -> None:
    capture = FakeVideoCapture()
    monkeypatch.setattr(opencv_capture.cv2, "VideoCapture", lambda: capture)

    returned = opencv_capture.create_opencv_capture(
        "rtsp://camera.local/live",
        open_timeout_ms=4_000,
        read_timeout_ms=750,
        buffer_size=1,
        decoder_threads=1,
    )

    assert returned is capture
    assert capture.open_args == (
        "rtsp://camera.local/live",
        opencv_capture.cv2.CAP_FFMPEG,
        [
            opencv_capture.cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            4_000,
            opencv_capture.cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            750,
            opencv_capture.cv2.CAP_PROP_N_THREADS,
            1,
        ],
    )
    assert capture.set_calls == [(opencv_capture.cv2.CAP_PROP_BUFFERSIZE, 1)]


def test_non_rtsp_capture_keeps_automatic_backend(monkeypatch) -> None:
    capture = FakeVideoCapture()
    monkeypatch.setattr(opencv_capture.cv2, "VideoCapture", lambda: capture)

    opencv_capture.create_opencv_capture("sample.avi")

    assert capture.open_args == ("sample.avi",)


def test_runtime_capture_options_are_configurable() -> None:
    original = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
    try:
        opencv_capture.configure_ffmpeg_capture_options("rtsp_transport;tcp")
        assert os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] == "rtsp_transport;tcp"
    finally:
        if original is None:
            os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
        else:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = original
