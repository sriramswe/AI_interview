# Collaborative development workflow

The authenticated API coordinates a planning agent, parallel backend/database/frontend agents, and an integration agent. The resulting proposals are persisted per user and task. After integration, the workflow waits for real test results from the operator. A failed result starts the debugging agent and permits a retest; a passing result produces a deployment checklist. Deployment confirmation then unlocks monitoring report analysis.

## API sequence

All routes require the application's bearer-token authentication.

1. `POST /api/development/workflows` with `{"task_description":"..."}` starts planning and returns the plan, parallel proposals, and integration output.
2. `POST /api/development/workflows/{id}/test-results` with `{"passed":false,"summary":"..."}` records actual test evidence and asks Testing/Debugging agents to analyze failures. Submit the real rerun result on retry. Five attempts are allowed. A passing result advances to deployment preparation.
3. `POST /api/development/workflows/{id}/deployment` confirms that a human/operator deployed the change. Optionally include `deployment_url` and `notes`.
4. `POST /api/development/workflows/{id}/monitoring` with `{"status":"healthy","details":"..."}` records an operator-provided health report and lets the Monitoring Agent summarize it. A degraded report ends in the `degraded` state.
5. `GET /api/development/workflows` lists the current user's workflows; `GET /api/development/workflows/{id}` retrieves one.

## Safety and execution boundaries

These are proposal-generating agents, not an unattended coding/deployment service. They do not have repository filesystem, shell, CI, cloud, or live-monitoring access; generated code and migration guidance must be reviewed and applied by a developer. The Testing Agent analyzes a result supplied by the operator and does not run tests itself. Deployment and health checks must be performed by the deployment platform/operator. Configure the backend AI provider before creating workflows; task descriptions are sent to that configured provider.
