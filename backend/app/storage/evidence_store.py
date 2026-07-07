from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2

from app.camera.types import FrameArray


REPO_ROOT = Path(__file__).resolve().parents[3]


class EvidenceStore:
    def __init__(self, root_directory: Path) -> None:
        if root_directory.is_absolute():
            self.root_directory = root_directory
        else:
            self.root_directory = (REPO_ROOT / root_directory).resolve()

    def save(
        self,
        detection_id: str,
        frame: FrameArray,
        timestamp: datetime,
    ) -> str:
        relative_path = Path(
            f"{timestamp:%Y}",
            f"{timestamp:%m}",
            f"{timestamp:%d}",
            f"{detection_id}.jpg",
        )
        absolute_path = self.root_directory / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        ok = cv2.imwrite(str(absolute_path), frame)
        if not ok:
            raise OSError(f"failed to save evidence image: {absolute_path}")
        return relative_path.as_posix()

    def resolve(self, relative_path: str) -> Path:
        path = (self.root_directory / relative_path).resolve()
        root = self.root_directory.resolve()
        if root not in path.parents and path != root:
            raise ValueError("evidence path escapes evidence directory")
        return path
