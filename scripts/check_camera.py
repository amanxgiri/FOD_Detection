import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.camera import CameraManager, LatestFrameBuffer


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture one frame from a camera source.")
    parser.add_argument(
        "--source",
        default="0",
        help="OpenCV camera index or local video path. Defaults to 0.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Seconds to wait for the source to open.",
    )
    args = parser.parse_args()

    buffer = LatestFrameBuffer()
    manager = CameraManager(args.source, buffer, reconnect_delay_seconds=0.2)

    try:
        packet = manager.capture_one(open_timeout_seconds=args.timeout)
    except Exception as exc:
        print(f"camera check failed: {exc}")
        return 1

    height, width = packet.frame.shape[:2]
    print(
        "camera check passed: "
        f"sequence_id={packet.sequence_id} "
        f"captured_at={packet.captured_at.isoformat()} "
        f"shape={width}x{height}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
