import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.inference.model_adapter import ModelIntegrationError
from app.inference.model_adapter import TensorRTModelAdapter
from app.inference.model_loader import (
    validate_engine_model,
    validate_source_model,
)


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Validate configured model artifacts.")
    parser.add_argument("--source", type=Path, default=settings.model_source_path)
    parser.add_argument("--engine", type=Path, default=settings.model_engine_path)
    parser.add_argument(
        "--require-engine",
        action="store_true",
        help="Require the TensorRT engine to exist and have the expected suffix.",
    )
    parser.add_argument(
        "--load-engine",
        action="store_true",
        help="Attempt to load the configured TensorRT adapter.",
    )
    args = parser.parse_args()

    try:
        validate_source_model(args.source)
        print(f"source model available: {args.source}")
        if args.require_engine or args.load_engine:
            validate_engine_model(args.engine)
            print(f"TensorRT engine available: {args.engine}")
        if args.load_engine:
            adapter = TensorRTModelAdapter(args.engine, settings.model_device)
            adapter.load()
            adapter.warmup()
            adapter.close()
            print("TensorRT adapter loaded and warmed up")
    except ModelIntegrationError as exc:
        print(f"model check failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
