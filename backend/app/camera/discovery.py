from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from urllib.request import urlopen

from fastapi import FastAPI

from app.api.websocket.events import make_event
from app.core.lifecycle import get_runtime_controller
from app.core.logging import get_logger
from app.storage.repositories.camera_repository import CameraRepository

logger = get_logger(__name__)
HOSTNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class MediaMtxDiscoveryService:
    def __init__(self, app: FastAPI) -> None:
        self._app = app
        self._settings = app.state.settings
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._online_ids: set[str] = set()
        self._suppressed_until_offline: set[str] = set()
        self.status = "starting"
        self.warning: str | None = None

    def suppress_until_disconnect(self, camera_id: str) -> None:
        """Keep a forgotten live publisher hidden until it disconnects once."""
        self._suppressed_until_offline.add(camera_id.lower())

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="mediamtx-camera-discovery")

    async def stop(self) -> None:
        self._stop_event.set()
        task = self._task
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._task = None

    async def scan_once(self) -> None:
        try:
            paths_payload, sessions_payload = await asyncio.gather(
                asyncio.to_thread(self._get_json, "/v3/paths/list"),
                asyncio.to_thread(self._get_json, "/v3/rtspsessions/list"),
            )
            await self._reconcile(paths_payload, sessions_payload)
            self.status = "online"
        except Exception as exc:
            self.status = "unavailable"
            self.warning = f"MediaMTX discovery unavailable: {exc}"
            logger.warning(self.warning)
            await self._app.state.websocket_manager.broadcast_warning(self.warning)
        finally:
            try:
                get_runtime_controller(self._app).reconcile_inference_lanes()
            except Exception as exc:
                logger.warning("could not reconcile dynamic inference lanes: %s", exc)

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.scan_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._settings.camera_discovery_interval_seconds,
                )
            except TimeoutError:
                pass

    async def _reconcile(
        self, paths_payload: dict[str, Any], sessions_payload: dict[str, Any]
    ) -> None:
        publisher_ips = {
            item.get("path"): _remote_ip(item.get("remoteAddr"))
            for item in sessions_payload.get("items", [])
            if item.get("state") == "publish" and item.get("path")
        }
        ready_paths = {
            item["name"]: item
            for item in paths_payload.get("items", [])
            if item.get("ready") is True
            and isinstance(item.get("name"), str)
            and HOSTNAME_PATTERN.fullmatch(item["name"].lower())
            and _has_h264(item)
        }
        ready_ids = {path_name.lower() for path_name in ready_paths}
        self._suppressed_until_offline.intersection_update(ready_ids)
        now = datetime.now(UTC)
        controller = get_runtime_controller(self._app)
        discovered_now: set[str] = set()
        events: list[tuple[str, dict[str, Any]]] = []
        scan_warning: str | None = None
        session_factory = self._app.state.session_factory
        with session_factory() as session:
            repository = CameraRepository(session)
            existing = {record.id: record for record in repository.list_all()}
            for path_name in sorted(ready_paths):
                camera_id = path_name.lower()
                if camera_id in self._suppressed_until_offline:
                    continue
                if camera_id not in existing and len(existing) >= self._settings.camera_max_count:
                    scan_warning = (
                        f"Camera capacity {self._settings.camera_max_count} reached; "
                        f"ignored publisher {camera_id}"
                    )
                    continue
                record, created = repository.upsert_discovered(
                    camera_id=camera_id,
                    rtsp_path=path_name,
                    publisher_ip=publisher_ips.get(path_name),
                    seen_at=now,
                )
                existing[camera_id] = record
                discovered_now.add(camera_id)
                controller.add_camera(
                    record.id, record.rtsp_path, record.selected_model_id
                )
                if created:
                    events.append(("camera.discovered", {"camera_id": camera_id}))

        for camera_id in discovered_now - self._online_ids:
            events.append(("camera.online", {"camera_id": camera_id}))
        for camera_id in self._online_ids - discovered_now:
            events.append(("camera.offline", {"camera_id": camera_id}))
        for camera_id in discovered_now:
            try:
                controller.set_camera_online(camera_id, True)
            except Exception as exc:
                scan_warning = f"Could not activate inference for {camera_id}: {exc}"
        for camera_id in self._online_ids - discovered_now:
            controller.set_camera_online(camera_id, False)
        self._online_ids = discovered_now
        self.warning = scan_warning
        manager = self._app.state.websocket_manager
        for event_type, data in events:
            await manager.broadcast(make_event(event_type, data))
        if scan_warning is not None:
            await manager.broadcast_warning(scan_warning)

    def _get_json(self, path: str) -> dict[str, Any]:
        url = f"{self._settings.mediamtx_api_url.rstrip('/')}{path}"
        with urlopen(url, timeout=2.0) as response:  # noqa: S310 - configured local service
            return json.load(response)


def _has_h264(path_item: dict[str, Any]) -> bool:
    tracks = path_item.get("tracks", [])
    if "H264" in tracks:
        return True
    return any(track.get("codec") == "H264" for track in path_item.get("tracks2", []))


def _remote_ip(remote_address: Any) -> str | None:
    if not isinstance(remote_address, str) or not remote_address:
        return None
    if remote_address.startswith("[") and "]:" in remote_address:
        return remote_address[1:].split("]:", 1)[0]
    return remote_address.rsplit(":", 1)[0]
