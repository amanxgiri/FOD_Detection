from datetime import UTC, datetime
from pathlib import Path
import struct
import zlib

import numpy as np

from app.camera.source_timestamp import decode_source_timestamp, source_identity_matches
from app.inference.model_catalog import ModelCatalog
from app.storage import create_database_engine, create_session_factory, init_database
from app.storage.repositories.camera_repository import CameraRepository


def test_model_catalog_exposes_only_ready_engines(tmp_path: Path) -> None:
    (tmp_path / "model_1.engine").touch()
    (tmp_path / "model_2.engine").touch()
    (tmp_path / "model_3.onnx").touch()
    (tmp_path / "model_4.pt").touch()

    entries = ModelCatalog(tmp_path).list_ready()

    assert [entry.id for entry in entries] == ["model_1", "model_2"]


def test_camera_registration_preserves_name_and_assignment_on_reconnect(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'registry.db'}")
    init_database(engine)
    factory = create_session_factory(engine)
    first_seen = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
    second_seen = datetime(2026, 8, 16, 10, 5, tzinfo=UTC)
    with factory() as session:
        repository = CameraRepository(session)
        record, created = repository.upsert_discovered(
            "raspberrypi9", "raspberrypi9", "192.168.1.204", first_seen
        )
        assert created
        repository.update_display_name(record.id, "Runway north")
        repository.update_model(record.id, "model_2")
        reconnected, created = repository.upsert_discovered(
            "raspberrypi9", "raspberrypi9", "192.168.1.214", second_seen
        )

    assert not created
    assert reconnected.display_name == "Runway north"
    assert reconnected.selected_model_id == "model_2"
    assert reconnected.publisher_ip == "192.168.1.214"
    assert reconnected.last_seen_at.replace(tzinfo=UTC) == second_seen


def test_decodes_hostname_v2_marker_and_matches_configured_camera() -> None:
    hostname = "raspberrypi11"
    sequence_id = 73
    captured_at = datetime(2026, 8, 16, 10, 20, 30, 123456, tzinfo=UTC)
    identity = zlib.crc32(hostname.encode()) & 0xFFFFFFFF
    body = struct.pack(
        ">2sBIIQ", b"FD", 2, identity, sequence_id,
        int(captured_at.timestamp() * 1_000_000),
    )
    marker = body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    frame = np.full((720, 1280, 3), 90, dtype=np.uint8)
    bits = [(byte >> shift) & 1 for byte in marker for shift in range(7, -1, -1)]
    left = frame.shape[1] - 8 - (92 * 6)
    for index, bit in enumerate(bits):
        row, column = divmod(index, 92)
        frame[8 + row * 6 : 14 + row * 6, left + column * 6 : left + (column + 1) * 6] = 255 if bit else 0

    decoded = decode_source_timestamp(frame)

    assert decoded is not None
    assert decoded.sequence_id == sequence_id
    assert decoded.captured_at == captured_at
    assert source_identity_matches(hostname, decoded.camera_id)
    assert not source_identity_matches("raspberrypi9", decoded.camera_id)
