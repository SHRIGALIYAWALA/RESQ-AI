# Production Runbook

## Launch

1. Install Docker Engine on a Linux production host, or Docker Desktop on Windows only after verifying its license for your organization. Install PostgreSQL client tools on the operator host.
2. Create `deploy/certs/fullchain.pem` and `deploy/certs/privkey.pem` from a certificate issued for the deployment hostname. Never commit them.
3. Set `POSTGRES_PASSWORD`, `AUTH_SECRET`, and `CORS_ORIGINS` in the deployment environment.
4. Start the stack: `docker compose -f docker-compose.production.yml up -d --build`.
5. Initialize or upgrade the schema: `docker compose -f docker-compose.production.yml exec app python -m backend.database.migrate`.
6. Verify `/health`, `/ready`, and `/api/health/providers` through HTTPS.
7. Run `scripts/production_acceptance.ps1 -BaseUrl https://hostname` and retain the output with the deployment record.
8. From the backend host's network path, run `scripts/test_camera_stream.ps1 -CameraStreamUrl http://PHONE-IP:8080/video`. This verifies that the exact URL responds with MJPEG and supplies two complete JPEG frames; it does not replace checking moving video and positive FPS in RESQ-AI.

## Backups

Run `scripts/backup_postgres.ps1` from a host with PostgreSQL client tools. Store dumps outside the host, encrypt them at rest, retain multiple generations, and perform a restore drill at least monthly. A backup that has never been restored is not a recovery plan.

## Device gateways

Camera and sensor gateways must send authenticated HTTPS requests using the operator JWT or a dedicated gateway identity. Sensor readings use `POST /api/buildings/{building_id}/sensor-readings` with `sensor_id`, `sensor_type`, `value`, `source`, and optional `hazard`. Camera observations use `POST /api/buildings/{building_id}/vision` with `camera_id`, `observations`, `floor`, and `zone`. Every gateway event remains advisory and requires operator review before escalation.

## Notification relay

The production compose stack uses the open-source local `ntfy` relay. Operators subscribe to the `resq-alerts` topic using an approved internal client. For SMTP or another internal webhook, replace `NOTIFICATION_WEBHOOK_URL` and test a delivered, failed, and fallback notification before go-live.

## Operational controls

- Rotate `AUTH_SECRET` using a planned token invalidation window.
- Restrict PostgreSQL network access to the app and backup hosts.
- Use a real hostname certificate and keep port 80 only for redirect.
- Alert on `/ready` failures, notification fallback status, database disk usage, backup age, and provider errors.
- Keep human approval enabled. RESQ-AI is decision support and does not dispatch emergency services autonomously.
