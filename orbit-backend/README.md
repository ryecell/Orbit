# Orbit API

FastAPI backend for the Orbit app: auth, folders/items, tasks, reminders,
real-time group chat, and server-side AI auto-tagging.

## Quick start (local dev, SQLite, zero setup)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."       # required for /ai/analyze
export ORBIT_SECRET_KEY="something-random"   # see note below
export ORBIT_ALLOWED_ORIGINS="http://localhost:5173"

uvicorn main:app --reload --port 8000
```

No `DATABASE_URL`? It defaults to a local `orbit.db` SQLite file, created
automatically. No `SMTP_HOST`? Verification links print to the console
instead of emailing. Both are safe, working defaults for development.

If you've run an older version of this backend before, delete `orbit.db` —
the schema has changed and there's no migration path from pre-Alembic
databases.

**Identity model:** `username` is the account identifier — required, unique,
used for login. `email` is optional, addable later from Profile settings,
and used only for verification and password-reset emails. An account with
no email has no way to recover a forgotten password; that's a deliberate
signup-friction tradeoff, not an oversight.

Visit `http://localhost:8000/docs` for interactive API docs.

## Production setup

**1. Database — Postgres via Alembic migrations**

```bash
export DATABASE_URL="postgresql://user:password@host:5432/orbit"
alembic upgrade head
```

SQLite is fine for local dev but gets wiped on every deploy/restart on most
hosting platforms, so production needs real Postgres. `alembic upgrade head`
creates the schema; run it once before the app's first start, and again
after pulling any future migration. The `Procfile`'s `release` step does
this automatically on platforms that support release phases (Render,
Heroku-style).

To add a new migration after changing `models.py`:
```bash
alembic revision --autogenerate -m "describe the change"
# review the generated file in alembic/versions/ before committing
alembic upgrade head
```

**2. Email — SMTP**

```bash
export SMTP_HOST="smtp.yourprovider.com"
export SMTP_PORT="587"
export SMTP_USER="..."
export SMTP_PASSWORD="..."
export SMTP_FROM="no-reply@yourdomain.com"
export ORBIT_PUBLIC_API_URL="https://api.yourdomain.com"   # used to build the verify link
export ORBIT_PUBLIC_FRONTEND_URL="https://yourapp.vercel.app"  # used to build the password-reset link
```

Plain SMTP (stdlib `smtplib`, no vendor SDK) so this works unmodified with
AWS SES, Postmark, SendGrid, or Mailgun's SMTP relay — just point it at
their SMTP host and credentials. If sending fails for any reason, it falls
back to printing the link and logs a warning rather than breaking
registration.

**3. Rate limiting storage — Redis (only if running more than one instance)**

```bash
export REDIS_URL="redis://user:password@host:6379/0"
```

Without this, rate limits are tracked in-memory per process — fine for a
single instance, but multiple instances (or autoscaling) won't share state,
so limits become easy to bypass by hitting different instances.

**4. Error monitoring — Sentry (optional)**

```bash
export SENTRY_DSN="https://...@sentry.io/..."
```

**5. Deploying**

- `Dockerfile` — builds a container that runs `uvicorn` with `--proxy-headers`
  (so it trusts `X-Forwarded-*` from your platform's load balancer/TLS
  termination).
- `Procfile` — for Render/Heroku-style platforms; runs migrations as a
  release step, then starts the web process.
- `.github/workflows/ci.yml` — installs dependencies and import-checks the
  app on every push/PR.

Whatever you use, make sure it terminates HTTPS — nothing in this app does
that itself.

## Key endpoints

| Method | Path                          | Notes                          |
|--------|-------------------------------|---------------------------------|
| POST   | `/auth/register`              | Creates a user (unverified) + seeds default folders |
| POST   | `/auth/login`                 | Returns a JWT; locks out after repeated failures |
| POST   | `/auth/logout`                | Revokes the current token       |
| GET    | `/auth/verify?token=...`      | Marks the account verified      |
| POST   | `/auth/resend-verification`   | Re-sends the verification email |
| POST   | `/auth/forgot-password`       | Always returns a generic response, emails a reset link if the account exists |
| POST   | `/auth/reset-password`        | Sets a new password from a valid reset token; invalidates existing sessions |
| GET    | `/me`                         | Current user                    |
| PATCH  | `/me/email`                   | Link or change the account's email (optional at signup) |
| GET/POST | `/folders`                  | List / create folders           |
| POST   | `/folders/{id}/items`         | Add an archive item             |
| GET/POST/PATCH/DELETE | `/tasks`, `/tasks/{id}` | To-do management          |
| GET/POST | `/reminders`                | Smart reminders                 |
| GET/POST | `/groups/{id}/messages`     | Chat history (REST)             |
| WS     | `/ws/groups/{id}?token=...`   | Live chat over WebSocket, auth required |
| POST   | `/ai/analyze`                 | Sends an image to Claude server-side, returns title/folder/tags/summary |

All routes except `/auth/*`, `/health`, and `/docs` require
`Authorization: Bearer <token>`.

## Connecting the frontend

Use the companion `orbit-frontend` project — it already talks to every
endpoint above, including the authenticated WebSocket. See its README.

## Security posture

What's implemented:

- **Passwords** — bcrypt hashed; must contain a letter and a number, 8-char minimum.
- **Auth tokens** — JWTs, 24-hour expiry, unique `jti` per token.
- **Session revocation** — `/auth/logout` invalidates that specific token immediately.
- **Account lockout** — 5 failed logins locks the account for 15 minutes;
  login errors don't reveal whether the email exists.
- **Email verification** — token-based, expires after 24h, now actually
  emailed via SMTP in production (prints to console in dev).
- **WebSocket auth** — validates the JWT before accepting the connection;
  sender identity comes from the token, never the client message.
- **Rate limiting** — per-IP: register 5/min, login 10/min, AI analyze
  15/min, resend-verification 3/min. Redis-backed if `REDIS_URL` is set,
  otherwise in-memory (single process only).
- **Upload size cap** — `/ai/analyze` rejects images over ~8MB.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`.
- **Safe-by-default config** — no hardcoded fallback secret key, no CORS
  wildcard by default; both warn loudly if unset.
- **Authorization** — every query scoped to `owner_id`.
- **SQL injection protection** — SQLAlchemy ORM, parameterized throughout.
- **Structured logging** (`logging_config.py`) for security-relevant events
  (lockouts, revocations, email failures) — bootstrap warnings (missing
  secret/CORS config) stay as plain `print()` so they're visible even before
  logging is configured.
- **Error monitoring** — optional Sentry integration (`SENTRY_DSN`).
- **Real, migrated database** — Postgres via Alembic in production; SQLite
  for zero-setup local dev.

Known gaps, deliberately left as-is:

- **Token in `localStorage`** on the frontend — XSS-exposed. Switching to an
  httpOnly cookie trades that for CSRF exposure, which needs its own
  mitigation to be a net improvement, so it's left as Bearer-token auth.
- **No refresh tokens** — 24h hard expiry means daily re-login.
- **No CAPTCHA/bot protection** on registration.
- **No automated backups configured** — set these up on whatever Postgres
  host you use; most managed providers (RDS, Supabase, Neon, Render Postgres)
  offer this as a checkbox, not something this repo can do for you.
- **No privacy policy / terms of service** — needed before real users create
  accounts and upload personal photos/notes, and before those images get
  sent to Anthropic's API. This is a legal/product task, not a code one.
- **No hard spending cap on the Anthropic account** — the app-level rate
  limit helps, but set a billing alert/limit on the Anthropic account itself
  too, in case of abuse or a bug.

## Before deploying for real

- Set a strong random `ORBIT_SECRET_KEY`, kept out of version control.
- Restrict `ORBIT_ALLOWED_ORIGINS` to your real frontend domain(s).
- Set `DATABASE_URL` to Postgres and run `alembic upgrade head`.
- Configure SMTP so verification emails actually send.
- Put this behind HTTPS (reverse proxy or platform-provided TLS).
- Never commit your `ANTHROPIC_API_KEY`, `SMTP_PASSWORD`, or `DATABASE_URL`.
