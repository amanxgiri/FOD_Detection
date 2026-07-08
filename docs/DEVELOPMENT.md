# Development

This repository follows the milestone sequence in `Technical_Design_Documentation.md`.

Milestone 1 establishes the backend and frontend foundation only. Camera capture,
model inference, streaming, persistence, alerts, and monitoring are intentionally
implemented in later milestones.

The backend supports Python 3.12 through 3.14. The dependency pins are kept
compatible with Python 3.14 so a fresh deployment machine can install the
runtime stack without building unsupported native wheels.
