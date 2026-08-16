#!/usr/bin/env python3
"""Seed the original three Pis in the dynamic camera registry."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.storage import create_database_engine, create_session_factory, init_database  # noqa: E402
from app.storage.repositories.camera_repository import CameraRepository  # noqa: E402

CAMERAS = (
    ("raspberrypi7", "192.168.1.203", "model_1"),
    ("raspberrypi9", "192.168.1.204", "model_2"),
    ("raspberrypi11", "192.168.1.205", "model_3"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=get_settings().database_url)
    args = parser.parse_args()
    engine = create_database_engine(args.database_url)
    init_database(engine)
    session_factory = create_session_factory(engine)
    now = datetime.now(UTC)
    with session_factory() as session:
        repository = CameraRepository(session)
        for hostname, publisher_ip, model_id in CAMERAS:
            record, _ = repository.upsert_discovered(
                camera_id=hostname,
                rtsp_path=hostname,
                publisher_ip=publisher_ip,
                seen_at=now,
            )
            repository.update_model(record.id, model_id)
            print(f"{hostname}: /{hostname} -> {model_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
