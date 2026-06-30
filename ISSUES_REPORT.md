# GiSTo Local Setup Issues Report

## 1. Database and Alembic Migrations
- **Issue**: The Alembic migration `97c4eb531e30_initial_schema.py` used the uppercase *names* of the Python enums (e.g., `'ACTIVE'`, `'PURCHASE'`) instead of their actual lowercase *values* (e.g., `'active'`, `'purchase'`). This caused a schema mismatch when SQLAlchemy attempted to insert lowercase strings into uppercase enum columns in PostgreSQL.
- **Fix**: Updated all `sa.Enum` declarations in the migration to use the correct lowercase values.
- **Verification**: Static Fix applied. (Terminal sandbox prevented running `python -m scripts.seed` and the smoke tests. See note below.)

## 2. Backend CORS Configuration
- **Issue**: The backend's `allow_origins=["*"]` works for basic usage but can cause issues for dashboards running locally (like Vite's dev server) if the frontend requires specific origin matching.
- **Fix**: Updated `allow_origins` in `backend/app/main.py` to explicitly include `"http://localhost:5173"` and `"http://127.0.0.1:5173"`.
- **Verification**: Static Fix applied.

## 3. Bot Handlers Wiring
- **Issue**: Running `bot/app/main.py` directly without a `TELEGRAM_BOT_TOKEN` set raised a `RuntimeError`, breaking the ability to easily test the handler wiring locally using a dummy token as intended.
- **Fix**: Rewrote `main()` in `bot/app/main.py` to fall back to a dummy token (`"dummy_token_for_testing"`) if none is provided. In this fallback test mode, it builds the application to verify wiring and then gracefully skips `run_polling()` to avoid network errors.
- **Verification**: Static Fix applied.

## 4. Dashboard API Base URL
- **Issue**: The dashboard API client in `dashboard/src/api/client.js` defaulted to `'http://localhost:8000'` if `VITE_BACKEND_BASE_URL` was missing. While fine for dev, this breaks production builds because it would still attempt to connect to localhost instead of the host origin.
- **Fix**: Changed the fallback to `import.meta.env.PROD ? '' : 'http://localhost:8000'`. In a production build, it now defaults to the current origin.
- **Verification**: Static Fix applied.

---

**Execution Note**: 
The terminal sandbox environment failed to open standard IO pipes (`opening NUL for ACL write: Access is denied`) across all commands (Python, npm, etc). Therefore, the exact test execution output ("ALL SMOKE TESTS PASSED", Vite build output) cannot be provided in this report, as the platform entirely blocked executing the local servers and test suites. All identified issues have been successfully fixed statically based on source code analysis.
