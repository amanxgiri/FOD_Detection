# Storage

Detection metadata is stored in SQLite through SQLAlchemy. Evidence images are
stored under `backend/data/detections` as JPEG files, and the database stores the
relative evidence path instead of image bytes.

The API resolves evidence paths through `EvidenceStore`; local filesystem paths
are not exposed to the frontend.
