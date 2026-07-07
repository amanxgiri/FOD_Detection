import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.inference.model_adapter import ModelIntegrationError
from app.inference.tensorrt_export import (
    TensorRTExportConfig,
    export_tensorrt_engine,
    format_export_config,
    validate_cuda_available,
)


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Export model_weight.pt to TensorRT.")
    parser.add_argument("--source", type=Path, default=settings.model_source_path)
    parser.add_argument("--engine", type=Path, default=settings.model_engine_path)
    parser.add_argument("--device", default=settings.model_device)
    parser.add_argument("--image-size", type=int, default=settings.model_image_size)
    parser.add_argument("--workspace", type=int, default=None)
    parser.add_argument("--fp32", action="store_true", help="Disable FP16 export.")
    parser.add_argument(
        "--check-prerequisites-only",
        action="store_true",
        help="Validate CUDA prerequisites without writing an engine.",
    )
    args = parser.parse_args()

    config = TensorRTExportConfig(
        source_path=args.source,
        engine_path=args.engine,
        device=args.device,
        image_size=args.image_size,
        half=not args.fp32,
        workspace=args.workspace,
    )
    print(format_export_config(config))

    try:
        if args.check_prerequisites_only:
            validate_cuda_available(config.device)
            print("TensorRT export prerequisites passed")
            return 0
        engine_path = export_tensorrt_engine(config)
    except ModelIntegrationError as exc:
        print(f"TensorRT export failed: {exc}")
        return 1

    print(f"TensorRT engine created: {engine_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
