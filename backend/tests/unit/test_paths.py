from pathlib import Path

from app.core import paths


def test_resolve_project_path_falls_back_to_repo_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_root = tmp_path
    nested_cwd = project_root / "backend"
    engine = project_root / "backend" / "models" / "weights" / "model_weight.engine"
    engine.parent.mkdir(parents=True)
    engine.write_bytes(b"engine")
    nested_cwd.mkdir(exist_ok=True)

    monkeypatch.setattr(paths, "PROJECT_ROOT", project_root)
    monkeypatch.chdir(nested_cwd)

    resolved = paths.resolve_project_path(
        Path("backend/models/weights/model_weight.engine")
    )

    assert resolved == engine
