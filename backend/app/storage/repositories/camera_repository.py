from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.models import CameraRegistration


class CameraRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[CameraRegistration]:
        statement = select(CameraRegistration).order_by(CameraRegistration.discovered_at)
        return list(self.session.scalars(statement))

    def get(self, camera_id: str) -> CameraRegistration | None:
        return self.session.get(CameraRegistration, camera_id)

    def get_by_rtsp_path(self, rtsp_path: str) -> CameraRegistration | None:
        return self.session.scalar(
            select(CameraRegistration).where(CameraRegistration.rtsp_path == rtsp_path)
        )

    def upsert_discovered(
        self,
        camera_id: str,
        rtsp_path: str,
        publisher_ip: str | None,
        seen_at: datetime | None = None,
    ) -> tuple[CameraRegistration, bool]:
        now = seen_at or datetime.now(UTC)
        record = self.get(camera_id)
        created = record is None
        if record is None:
            record = CameraRegistration(
                id=camera_id,
                rtsp_path=rtsp_path,
                publisher_ip=publisher_ip,
                discovered_at=now,
                last_seen_at=now,
                enabled=True,
            )
            self.session.add(record)
        else:
            record.rtsp_path = rtsp_path
            record.publisher_ip = publisher_ip
            record.last_seen_at = now
            record.enabled = True
        self.session.commit()
        self.session.refresh(record)
        return record, created

    def create_manual(
        self,
        camera_id: str,
        rtsp_url: str,
        display_name: str,
        publisher_ip: str | None,
    ) -> CameraRegistration:
        now = datetime.now(UTC)
        record = CameraRegistration(
            id=camera_id,
            display_name=display_name,
            rtsp_path=rtsp_url,
            publisher_ip=publisher_ip,
            discovered_at=now,
            last_seen_at=now,
            enabled=True,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update_display_name(
        self, camera_id: str, display_name: str | None
    ) -> CameraRegistration | None:
        record = self.get(camera_id)
        if record is None:
            return None
        record.display_name = display_name
        self.session.commit()
        self.session.refresh(record)
        return record

    def update_model(
        self, camera_id: str, model_id: str | None
    ) -> CameraRegistration | None:
        record = self.get(camera_id)
        if record is None:
            return None
        record.selected_model_id = model_id
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete(self, camera_id: str) -> bool:
        record = self.get(camera_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True
