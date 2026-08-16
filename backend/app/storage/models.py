from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class DetectionRecord(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    class_id: Mapped[int] = mapped_column(Integer, nullable=False)
    class_name: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x2: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y2: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class CameraRegistration(Base):
    __tablename__ = "camera_registrations"

    id: Mapped[str] = mapped_column(String(63), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rtsp_path: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    publisher_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selected_model_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
