# PrepEdge Live — Build Plan

Rebuild of an AI mock-interview platform. Single source of truth for scope, pages,
API surface, and schema. Tick items as phases complete.

Rules of engagement: original copy, names, and data (no text/branding copied from any
reference asset). All code written from scratch. One module per step; ≤ ~150 lines per
file; ask before installing anything large. Each phase: build → run → fix → commit → stop.

Product name: **PrepEdge Live** (given). Everything else invented by us: personas,
question banks, company profiles, tier names, marketing copy.

## Phases

- [x] 1. Plan — read brief, write this PLAN.md (pages, endpoints, models)
- [ ] 2. Backend scaffold — FastAPI app, `/health`, CORS, SQLAlchemy models
      (User, Interview, Message), DB init (create_all in dev, Alembic ready), `.env.example`
- [ ] 3. Interview API — `POST /interviews/start`, `POST /interviews/submit-answer`
      (5 questions → evaluation JSON: score, feedback, vibe_analysis) via mock AI
- [ ] 4. Frontend scaffold — Vite React, routes `/` `/login` `/dashboard` `/interview/:id`,
      Axios client, design tokens as CSS variables
- [ ] 5. Landing + Login UI — glassmorphism, animated gradient
- [ ] 6. Dashboard setup screen — 2 personas, 12 role categories (with sub-roles),
      difficulty 1–3, optional target company, panel toggle
- [ ] 7. Interview room UI — video tile, mic via Web Speech API, live transcript,
      submit answer, leave button
- [ ] 8. Evaluation screen — score, STAR analysis, vibe sub-scores
- [ ] 9. Resume upload — PDF text extraction (pypdf), ATS score endpoint + UI card
- [ ] 10. Company intelligence — our 20-company JSON injected into question prompts
- [ ] 11. Real Gemini provider — same service interface, `GEMINI_API_KEY`, mock fallback
- [ ] 12. Auth + pricing — Google OAuth + JWT, pricing page (UPI integration deferred)

## Pages (React)

| Route              | Phase | Purpose                                             |
|--------------------|-------|-----------------------------------------------------|
| `/`                | 5     | Landing: hero, features, flow explainer, pricing CTA |
| `/login`           | 5/12  | Email-lite demo login → later Google OAuth button    |
| `/dashboard`       | 4/6/9 | Setup form (persona/role/difficulty/company/panel), recent sessions, resume card |
| `/interview/:id`   | 7     | Interview room: video tile, mic, transcript, controls |
| `/evaluation/:id`  | 8     | Scorecard: total score, STAR breakdown, vibe analysis |
| `/pricing`         | 12    | Free vs Pro tiers (UPI paid checkout deferred)       |

## API endpoints (FastAPI, `/api` prefix)

| Method | Path                        | Phase | Purpose                                        |
|--------|-----------------------------|-------|------------------------------------------------|
| GET    | `/health`                   | 2     | Liveness + DB ping                             |
| GET    | `/config`                   | 6     | Personas, role categories, sub-roles, companies |
| POST   | `/interviews/start`         | 3     | Create session, generate Q1 via AI service     |
| POST   | `/interviews/{id}/submit-answer` | 3 | Store answer → next question or final evaluation |
| GET    | `/interviews/{id}`          | 3     | Full session state (transcript, meta)          |
| GET    | `/interviews/{id}/evaluation` | 8   | Final evaluation JSON                          |
| GET    | `/interviews`               | 8     | Recent sessions for dashboard                  |
| POST   | `/resume` (multipart)       | 9     | Upload PDF → extract text (pypdf)              |
| GET    | `/resume/{id}/ats`          | 9     | ATS score + breakdown                          |
| POST   | `/auth/google`              | 12    | Exchange Google id_token → our JWT             |
| POST   | `/auth/token`               | 12    | Demo email login → JWT                         |
| GET    | `/auth/me`                  | 12    | Current user from JWT                          |

## DB models (SQLAlchemy 2.0, SQLite)

- **User** — id, email (unique), name, avatar_url, google_sub, plan (`free|pro`),
  demo_password (optional, demo auth), created_at
- **Interview** — id, user_id FK, persona, role_category, sub_role, difficulty (1–3),
  target_company, panel_mode (bool), status (`active|completed|left`), score,
  evaluation (JSON), created_at, completed_at
- **Message** — id, interview_id FK, role (`interviewer|candidate`), content,
  question_number, created_at
- **Resume** (phase 9) — id, user_id FK, filename, raw_text, ats_score,
  ats_breakdown (JSON), created_at

## AI service layer (`services/ai/`)

Interface every provider implements:
- `generate_question(context, transcript) -> str` — interview-aware next question
- `evaluate(interview, transcript) -> dict` — `{score: 0-10, feedback: str,
  star_analysis: {situation, task, action, result}, vibe_analysis: {confidence,
  clarity, structure, enthusiasm, stress_tolerance}, strengths: [], improvements: []}`

Providers: `mock` (canned question banks + deterministic evaluation, zero deps),
`gemini` (Phase 11, same interface). Selected by `AI_PROVIDER` env / key presence.

## Authored data (ours)

- 2 personas: distinct temperament + interview style (friendly coach vs. hard grader)
- 12 role categories, each 2–4 sub-roles, each sub-role ≥ 4 seed questions (mock mode)
- 20-company intelligence JSON: name, sector, engineering focus, interview flavor,
  example themes — original descriptions, drives prompt injection (phase 10)

## Env (`.env.example`)

`GEMINI_API_KEY`, `AI_PROVIDER=mock|gemini`, `DATABASE_URL`, `CORS_ORIGINS`,
`JWT_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FRONTEND_URL`

## Layout

```
backend/  app/{main,config,database,models,schemas}.py, routers/, services/
frontend/ src/{pages,components,lib,styles}, vite via npm create (ask before install)
reference/ PLAN.md (this file)
```
