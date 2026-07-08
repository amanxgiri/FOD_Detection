# API

The initial API prefix is `/api/v1`.

Milestone 1 endpoints:

- `GET /api/v1/health`
- `GET /api/v1/config`

Milestone 5 endpoint:

- `GET /api/v1/stream`

Milestone 6 endpoint:

- `GET /api/v1/system/status`

Milestone 7 endpoints:

- `GET /api/v1/detections`
- `GET /api/v1/detections/{detection_id}`
- `GET /api/v1/detections/{detection_id}/evidence`
- `POST /api/v1/detections/{detection_id}/acknowledge`

Milestone 9 endpoint:

- `WS /api/v1/ws/events`

Runtime control endpoints:

- `POST /api/v1/runtime/camera/start`
- `POST /api/v1/runtime/camera/stop`
- `POST /api/v1/runtime/inference/start`
- `POST /api/v1/runtime/inference/stop`
