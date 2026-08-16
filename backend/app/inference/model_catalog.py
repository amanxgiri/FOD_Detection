from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.paths import resolve_project_path


@dataclass(frozen=True)
class ModelCatalogEntry:
    id: str
    display_name: str
    engine_path: Path


class ModelCatalog:
    def __init__(self, directory: Path) -> None:
        self.directory = resolve_project_path(directory)

    def list_ready(self) -> list[ModelCatalogEntry]:
        if not self.directory.exists():
            return []
        return [
            ModelCatalogEntry(
                id=path.stem,
                display_name=path.stem.replace("_", " ").title(),
                engine_path=path.resolve(),
            )
            for path in sorted(self.directory.glob("*.engine"), key=lambda item: item.name)
            if path.is_file()
        ]

    def get(self, model_id: str) -> ModelCatalogEntry | None:
        return next((entry for entry in self.list_ready() if entry.id == model_id), None)
