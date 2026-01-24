# OPS CI API Testing Instructions

## Current status
- Tests require the OPS backend (`apps/api`) to be running with a seeded PostgreSQL database and `ops_mode=real`.
- **Automated tests have not been executed in this environment** because the API server was not running.

## Prerequisites
1. Start the backend:
   ```bash
   make api-dev
   ```
   or run `make dev` to bring up both API and web servers.
2. Ensure PostgreSQL credentials are exported (you can use `.env` or `DATABASE_URL`):
   ```
   export DATABASE_URL=postgresql://user:pass@localhost:5432/tobit_spa_db
   ```
3. Seed the CI data (each script connects to the same database):
   ```bash
   python apps/api/scripts/seed/seed_ci.py
   python apps/api/scripts/seed/seed_metrics.py
   python apps/api/scripts/seed/seed_events.py
   python apps/api/scripts/seed/seed_history.py
   ```
4. Confirm `/health` is reachable:
   ```bash
   curl http://localhost:8000/health
   ```

## Environment variables used by the pytest suite
- `OPS_BASE_URL` (default `http://localhost:8000`)
- `OPS_CI_ENDPOINT` (default `/ops/ci/ask`)
- `OPS_ASSUME_REAL_MODE` (default `true`)
- `OPS_SEED_FROM` / `OPS_SEED_TO` (default `2025-12-01` / `2025-12-31`)
- Optional: `OPS_CI_DB_DSN` or `DATABASE_URL` to retrieve real CI identifiers.

## Running the suite
1. With the backend and DB ready, execute:
   ```bash
   ./scripts/run_ops_ci_api_tests.sh
   ```
2. The script performs health checks, pytest (writing `artifacts/junit.xml` and raw JSON files), and then runs `python scripts/generate_test_report.py` to produce `TEST_REPORT.md`.

## Post-run artifacts
- `artifacts/junit.xml`
- `artifacts/ops_ci_api_summary.json`
- `artifacts/ops_ci_api_raw/*.json`
- `TEST_REPORT.md`

## Notes
- If the API server is not running or the database lacks the seed data above, the tests will fail immediately because they depend on real `ci` rows and related metrics.
