from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_project_path(path: Path) -> Path:
    if path.is_absolute() or path.exists():
        return path

    candidate = PROJECT_ROOT / path
    if candidate.exists():
        return candidate
    return path
