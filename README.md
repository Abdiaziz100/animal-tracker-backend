# Livestock Tracker — Backend

Flask + PostgreSQL API for the Livestock Tracker app.

## Stack
- Flask 3, application-factory pattern, organized as blueprints (`auth`, `animals`, `tracking`, `reports`, `alerts`)
- PostgreSQL via SQLAlchemy + Flask-Migrate (Alembic) for versioned schema migrations
- JWT auth (Flask-JWT-Extended) for the mobile app
- Per-animal device tokens for hardware GPS tags (no shared secret, no open endpoints)
- marshmallow for request validation

## Local setup

```bash
docker compose up -d   # starts Postgres locally (skip if you already have Postgres running)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # paste into JWT_SECRET_KEY in .env
export FLASK_APP=run.py
flask db upgrade
python run.py
```

## ⚠️ If you already have an existing database (upgrading from a previous version)

**Do not delete your existing `migrations/` folder or database.** This version adds a
new `alerts` table and an `inactivity_threshold_hours` column to `geofences`. To
apply just that incremental change without touching your existing data:

```bash
export FLASK_APP=run.py
flask db migrate -m "add alerts table and inactivity threshold"
flask db upgrade
```

This has been verified end-to-end: existing rows survive the upgrade intact, and
only the new table/column get added.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

61 tests covering auth, animal CRUD, cross-user isolation, device-token auth on
tracking updates, geofence math, rate limiting, admin role gating, and the new
alert system (geofence-transition alerts, inactivity detection, acknowledge
flows). These run automatically on every push via GitHub Actions.

## New in this version: Alert History

Previously, "Alerts" only showed animals *currently* outside the farm — if the
app wasn't open when an animal left and returned, there was no record of it.
This version adds:

- **Persistent alert log** — every time an animal crosses the geofence boundary
  (`LEFT_FARM` / `RETURNED`), a row is saved to the new `alerts` table, not just
  reflected in live status.
- **Inactivity detection** — if an animal hasn't reported a new GPS location in
  longer than a configurable threshold (default 6 hours, adjustable per-farm via
  `PUT /api/geofence`), an `INACTIVE` alert fires. This check runs lazily
  whenever `GET /api/alerts` is called (i.e., whenever the app is open and
  polling) rather than on a real background schedule — a reasonable
  approximation for this app's usage pattern, though a production deployment
  at larger scale would want a proper cron/worker for precision independent of
  whether anyone has the app open.
- **Acknowledge / mark-as-read** — `POST /api/alerts/<id>/acknowledge` and
  `POST /api/alerts/acknowledge-all`.

Duplicate-alert prevention: a new `INACTIVE` alert only fires once per
"stillness episode" — it won't spam a new alert every time the app polls while
the animal remains stationary; it only fires again after the animal has moved
and then gone still for another full threshold period.

## Security notes

- **`/api/tracking/update`** requires a per-animal `X-Device-Token` header,
  generated once when the animal is created and rotatable via
  `POST /api/animals/<id>/device-token`.
- **`/api/admin/users`** requires a valid JWT for a user with `role = "admin"`.
- **JWT secret**: the app refuses to start if `JWT_SECRET_KEY`/`DATABASE_URL`
  aren't set — no insecure default.
- **Rate limiting**: login is capped at 10/min per IP and 5/min per email
  (throttles both a single attacker and a distributed attack on one account).
  Registration: 10/hour per IP. GPS tracking updates: 30/min per device token.
  Rate limit state is in-memory — fine for a single-process deployment, but
  needs a Redis-backed store if scaled to multiple workers.
- Every write/read endpoint scopes to `user_id` from the JWT.

## API overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register | — | Create account |
| POST | /api/auth/login | — | Get JWT |
| GET/PUT | /api/auth/profile | JWT | View/edit profile |
| PUT | /api/auth/push-token | JWT | Register/refresh push token |
| GET/POST | /api/animals | JWT | List / create animals |
| GET/PUT/DELETE | /api/animals/\<id\> | JWT | Manage one animal |
| POST | /api/animals/\<id\>/device-token | JWT | Rotate device token |
| GET/POST | /api/animals/\<id\>/health | JWT | Health records |
| POST | /api/tracking/update | Device token | GPS tag reports a new location |
| GET | /api/animals/\<id\>/history | JWT | Location history |
| GET/PUT | /api/geofence | JWT | Farm boundary + inactivity threshold |
| GET | /api/alerts | JWT | Alert history (also triggers inactivity check) |
| POST | /api/alerts/\<id\>/acknowledge | JWT | Mark one alert read |
| POST | /api/alerts/acknowledge-all | JWT | Mark all alerts read |
| GET | /api/dashboard | JWT | Summary stats |
| GET | /api/report | JWT | Compliance report |
| GET | /api/admin/users | JWT (admin role) | List all users |
