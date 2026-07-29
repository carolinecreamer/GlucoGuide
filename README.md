# GlucoGuide

> [!WARNING]
> **Educational example only. Not clinically validated, not medical advice, and not for
> treatment decisions or production use.** Never change insulin or treat an emergency based
> on this software. Follow your prescribed plan and consult a qualified clinician.

GlucoGuide is an advisory-only diabetes pattern and regimen-support example. It imports
Dexcom CGM data, combines it with manually logged meals, exercise, insulin, and prescribed
settings, and produces explainable observations for the user and clinician.

It does **not** prescribe insulin, calculate an insulin dose, automatically change pump
settings, control a pump, or replace a clinician or emergency service.

## Project status

This repository demonstrates architecture and implementation patterns. It currently uses a
single configured demo user and lacks the authentication, clinical validation, regulatory
clearance, operational controls, and human-factors evidence required for real-world use.

## Repository

- `backend/`: FastAPI API, Dexcom OAuth/token handling, persistence, and advisory engine.
- `ios/`: SwiftUI iOS client generated with XcodeGen.
- `infra/`: Azure deployment starting point.
- `docs/`: architecture, safety, privacy, and product boundaries.

## Prerequisites

- Python 3.12 or newer
- Docker Desktop when using PostgreSQL
- macOS with Xcode 16 and XcodeGen for the iOS app
- Dexcom developer sandbox credentials

## Run the backend on Windows

```powershell
cd C:\GlucoGuide
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".\backend[test]"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Put the generated encryption key and your rotated Dexcom sandbox credentials in `.env`.
Do not commit `.env`.

For the quickest local start, keep the SQLite URL in `.env`:

```powershell
cd C:\GlucoGuide\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. The registered Dexcom sandbox redirect URI must exactly be:

```text
http://localhost:8000/api/v1/integrations/dexcom/callback
```

For PostgreSQL, start Docker and use the local password from `docker-compose.yml`:

```powershell
docker compose up -d postgres
```

```dotenv
DATABASE_URL=postgresql+asyncpg://glucoguide:<local-password>@localhost:5432/glucoguide
```

## Run the backend on macOS or Linux

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e "./backend[test]"
cd backend
python -m uvicorn app.main:app --reload
```

## Build the iOS app

On a Mac:

```bash
brew install xcodegen
cd ios
xcodegen generate
xcodebuild \
  -project GlucoGuide.xcodeproj \
  -scheme GlucoGuide \
  -sdk iphonesimulator \
  -destination "generic/platform=iOS Simulator" \
  CODE_SIGNING_ALLOWED=NO \
  build
```

The simulator can use `http://localhost:8000`. A physical iPhone cannot reach the backend
through its own `localhost`; use an HTTPS development tunnel and register that exact HTTPS
Dexcom callback.

## Run tests

```bash
cd backend
python -m pytest
```

## Current security boundary

The development vertical slice uses one configured demo user ID. Before any multi-user or
internet-facing deployment, replace it with validated Microsoft Entra External ID tokens,
per-user authorization, database migrations, private networking, monitored backups, consent
records, account deletion, and a completed clinical/regulatory review.

See [SECURITY.md](SECURITY.md), [docs/SAFETY.md](docs/SAFETY.md), and
[docs/PRIVACY.md](docs/PRIVACY.md) before modifying or deploying the project.

## Contributing and license

Contributions must preserve the advisory-only safety boundary described in
[CONTRIBUTING.md](CONTRIBUTING.md). This project is available under the [MIT License](LICENSE).
