# Deployment

## Backend on Render with MySQL

The root `render.yaml` defines a Python web service rooted at `backend`. Create the service from the repository's Render Blueprint. Provision MySQL separately, then provide these values in Render's environment settings:

- `MYSQL_URL`: the MySQL connection string using the `mysql+pymysql://` driver.
- `CORS_ORIGINS`: comma-separated frontend origins, including the production Vercel domain.
- `OPENROUTER_API_KEY`: required for all backend AI features; keep it in backend environment settings, never in frontend variables.
- `OPENROUTER_MODEL`: optional model override; local and Render defaults use `google/gemma-4-31b-it:free`, currently listed in OpenRouter's free catalog.
- `OPENROUTER_FALLBACK_MODELS`: comma-separated alternate models tried when the primary is rate-limited or returns no text. The default list ends with OpenRouter's free-model router (`openrouter/free`) to try another available free model.
- `OPENROUTER_SITE_URL`: optional OpenRouter attribution URL.
- `GOOGLE_CLIENT_ID`: OAuth client ID for backend token verification when using Google sign-in.
- `SUPER_ADMIN_EMAILS`: comma-separated email allowlist for trusted admin accounts. Matching accounts receive the persisted `admin` role at startup and on authentication (email matching is case-insensitive). Set this to the trusted admin's email in Render and redeploy/restart the service; these accounts can assign `user`/`admin` roles. Other accounts may be promoted to admin by an admin in the admin user table; do not remove the last trusted admin.
- `UPI_ID`, `UPI_PAYEE_NAME`, and `PAYMENT_REVIEWER_EMAILS`: required to enable manual UPI payments and review. Use the merchant's verified receiving UPI ID and an inbox belonging to an authorized reviewer. Keep the receiving ID in backend environment settings, not frontend variables or source control. Configure `SUPER_ADMIN_EMAILS` for the reviewer who will approve/reject receipts.

### Production CI/CD with GitHub Actions

The `Production CI/CD` workflow runs on pull requests and pushes to `master`. It compiles the backend Python modules, runs the backend test suite against a temporary GitHub Actions MySQL service, and runs the frontend Vite production build. On `master` only, it triggers the Render and Vercel production deploy hooks after both check jobs pass. TiDB remains hosted separately; CI uses its own temporary MySQL database and never connects to production data.

Configure these repository secrets under GitHub → **Settings → Secrets and variables → Actions**:

- `RENDER_DEPLOY_HOOK_URL`: create a production deploy hook in the Render backend service settings.
- `VERCEL_DEPLOY_HOOK_URL`: create a production deploy hook in the Vercel project, targeting the `master` branch.

Until both secrets exist, CI still runs but production deployment is explicitly skipped with a warning. After configuring the secrets, push to `master` or manually run the workflow on `master` to deploy. Turn off automatic Git-triggered deployments in both Render and Vercel so they cannot deploy a push before CI passes. Keep the deploy hooks configured for the production `master` branch. Render's existing `MYSQL_URL`, `CORS_ORIGINS`, AI/OAuth settings, and other service environment variables remain configured in Render; Vercel's `VITE_API_BASE_URL` and `VITE_GOOGLE_CLIENT_ID` remain configured in Vercel. Do not put TiDB credentials or application secrets in GitHub workflow files.

For local development, start the MySQL container from the repository root:

```powershell
docker compose up -d
```

The Compose service creates the `ai_interview_prep` database and persists its data in a Docker volume. Copy `backend/.env.example` to `backend/.env`; its `DB_*` values match the local Compose credentials. The backend also supports `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for hosted MySQL connections and enables certificate and hostname verification for non-local hosts. Render can continue using its existing `MYSQL_URL` setting. Start FastAPI after MySQL reports healthy. Stop the container with `docker compose down`; use `docker compose down -v` only when you intend to delete the local database data. Set the selected AI provider settings in `backend/.env` as well.

Render generates `JWT_SECRET_KEY`. On startup, SQLAlchemy `create_all` creates missing MySQL tables; it does not modify existing tables. The backend applies the additive `gender` and `role` columns to existing `users` tables at startup. Other schema changes must be applied and verified deliberately before deploying code that depends on them. Existing PostgreSQL/Neon records are not automatically copied or converted; migrate them separately if they must be retained. Do not commit credentials or paste them into frontend `VITE_*` variables.

## Frontend on Vercel

Import the repository into Vercel and set the project root to `frontend`. `frontend/vercel.json` supplies the Vite build, SPA fallback, and `same-origin-allow-popups` policy for Google sign-in popups. Set `VITE_API_BASE_URL` to the deployed backend URL in Vercel project settings; the local development `.env` targets `http://localhost:8001` only. To enable Google sign-in, set `VITE_GOOGLE_CLIENT_ID` to the same OAuth client ID configured on the backend, add the exact deployed frontend origin (scheme and hostname, without a path) to that OAuth client's Authorized JavaScript origins in Google Cloud, and add the origin to backend `CORS_ORIGINS`. The browser's “origin is not allowed” error cannot be fixed in application code until the real frontend origin is authorized. Redeploy after setting Vercel variables and update backend CORS configuration.

The authenticated project-help chat uses the configured backend AI provider. Super-admin operations are enforced by the backend `SUPER_ADMIN_EMAILS` allowlist, not by the frontend navigation or route. Admins can search users, suspend or restore access, assign or remove plans, delete accounts and relational user data, and approve or reject pending manual payments.

### Manual UPI subscription payments

1. In the backend hosting environment, set `UPI_ID` to the verified receiving UPI ID, `UPI_PAYEE_NAME` to the matching merchant name, and `PAYMENT_REVIEWER_EMAILS` to the reviewer email(s). Also set `SUPER_ADMIN_EMAILS` for the reviewer account that will use the admin console.
2. Deploy/restart the backend. The billing page generates a QR/UPI link using the configured ID and current Pro/Elite price. Checkout remains unavailable with a clear error until `UPI_ID` is set.
3. Candidates pay in their UPI app and submit the receipt screenshot and UPI transaction reference in the dashboard. Requests stay pending; a reviewer verifies the amount and transaction in the merchant's UPI/bank app and approves or rejects the receipt in the admin console.
4. The subscription activates only after an authorized admin approves it. This is a manual transfer-and-review flow, not automatic payment confirmation or a bank-integrated gateway; never approve based only on the uploaded screenshot.

## Model and browser feature requirements

- Configure `OPENROUTER_API_KEY` to use the backend's sole AI provider. The default free Gemma model can be overridden with `OPENROUTER_MODEL`; comma-separated OpenRouter alternates are configured with `OPENROUTER_FALLBACK_MODELS`. The default alternates end with OpenRouter's `openrouter/free` router, which tries another available free model. The backend tries all configured options in sequence if a model is rate-limited or returns no text, and reports an error if all options fail. This sends AI prompts, including interview and resume text, to OpenRouter for processing; free model availability and rate limits can change.
- MySQL stores interview history and relational data. Interview answers are evaluated using the configured backend NLP/model providers; no external vector database is required.
- Camera framing and voice-pitch estimates run locally in the browser and depend on browser support and user-granted permissions. They do not provide body-language, emotion, or confidence judgments.
- Calendar reminders are downloaded as local `.ics` files. LinkedIn sharing uses its public share link; OAuth integrations and voice/video cloning providers are not configured.
