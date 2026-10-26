# Production Acceptance Checklist

Complete this checklist on the target host. Do not mark RESQ-AI production-ready from local code checks alone.

## Host and deployment

- [ ] Docker Engine/Desktop installed and `docker compose version` succeeds.
- [ ] Host firewall exposes only HTTPS and approved administration paths.
- [ ] `docker compose -f docker-compose.production.yml config` succeeds.
- [ ] Production secrets are injected from a secret store or protected environment, not committed files.
- [ ] PostgreSQL volume is on durable storage with disk alerts.

## TLS

- [ ] Certificate matches the production hostname and is trusted by operator clients.
- [ ] `http://hostname` redirects to HTTPS.
- [ ] TLS 1.2/1.3 works and weak protocols are disabled.
- [ ] Private key permissions restrict access to the proxy service.

## Database and recovery

- [ ] `/ready` reports `database_backend: postgresql`.
- [ ] `python -m backend.database.migrate` completes successfully.
- [ ] A backup is created with `scripts/backup_postgres.ps1`.
- [ ] Backup is copied to protected off-host storage.
- [ ] Restore is performed into a disposable PostgreSQL database and verified.
- [ ] Backup schedule, retention, RPO, and RTO are written down.

## Identity and tenants

- [ ] `REQUIRE_AUTH=true` and a unique high-entropy `AUTH_SECRET` are active.
- [ ] Viewer cannot create incidents, change telemetry, reserve resources, or deliver alerts.
- [ ] An operator can access only their tenant's buildings and incidents.
- [ ] Cross-tenant building, incident, resource, camera, sensor, simulation, and audit requests return 404/403.
- [ ] Operator/admin accounts are provisioned through a controlled process, not public self-registration.

## Gateways and notifications

- [ ] A real sensor sends a reading over HTTPS and appears in the tenant's readings.
- [ ] A real camera sends an observation and the camera is validated against its building.
- [ ] `scripts/test_camera_stream.ps1` receives at least two complete frames from the phone's exact stream URL when run from the backend host's network path.
- [ ] The dashboard shows moving camera video and a positive FPS for at least 60 seconds.
- [ ] Disconnect and restart the phone stream; the dashboard reports the interruption and recovers without additional camera registrations.
- [ ] Duplicate/replayed gateway messages are handled by the gateway or an approved idempotency layer.
- [ ] A notification draft cannot deliver without explicit operator approval.
- [ ] ntfy, SMTP, or the approved internal webhook receives a test alert.
- [ ] Webhook failure produces a logged local fallback and an audit record.

## Scenario acceptance

- [ ] Fire: room alert, building escalation, operator review, and route/resource review.
- [ ] Medical: incident creation, triage review, notification draft, and approved delivery.
- [ ] Evacuation: building-wide alert, occupant acknowledgement process, and report export.
- [ ] Device failure: stale/offline sensor or camera is visible to operators.
- [ ] Health failure: database/provider failure generates a monitorable non-200 response.

Run `scripts/production_acceptance.ps1 -BaseUrl https://hostname` after completing the checklist. Production status requires signed-off evidence for every checked item.
