from pathlib import Path

from app.storage import (
    EvidenceStore,
    create_database_engine,
    create_session_factory,
    init_database,
)


def configure_test_storage(app: object, tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'fod-test.db'}")
    init_database(engine)
    app.state.database_engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.evidence_store = EvidenceStore(tmp_path / "evidence")
