# InterviewAI frontend

## Local development

1. Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` to the backend URL.
2. Set `VITE_GOOGLE_CLIENT_ID` if Google sign-in should be enabled; configure that same client ID in the backend.
3. Install dependencies with `npm ci`.
4. Run `npm run dev`, then open the Vite URL shown in the terminal.

Run `npm run lint` and `npm run build` before publishing.

## Source layout

- `src/App.jsx` coordinates authentication, interview, and billing state.
- `src/features/auth/` contains the sign-in screen and Google Identity button.
- `src/features/dashboard/` contains interview setup, plans/payment, and scheduling panels.
- `src/features/resume/` contains the experience/student/education setup flow, 30-template resume builder, and print-to-PDF preview.
- `src/features/interview/` contains the interview workspace and local camera/microphone analysis.
- `src/features/scheduling/` creates local calendar invite files.
- `src/services/` contains the shared API client and auth, interview, and billing API calls.
- `src/main.jsx` mounts the app; `src/index.css` and `src/App.css` contain global and application styles.

## Vercel

Create a Vercel project with the repository's `frontend` directory as its root. The included `vercel.json` configures the Vite build and SPA fallback. Set `VITE_API_BASE_URL` to the Render API URL (`https://ai-interview-10mb.onrender.com`) and, if using Google sign-in, `VITE_GOOGLE_CLIENT_ID` in the Vercel project environment variables for every environment you use, then redeploy. Production builds default to this Render URL if the API variable is missing or points to localhost; local development continues to default to `http://localhost:8001`.

The backend must allow the deployed frontend origin in its `CORS_ORIGINS` setting. Never put backend secrets in a `VITE_*` variable; Vite includes those values in public browser assets.

## Resume builder access

Signed-in users can create up to three saved resumes with templates for free. Active Elite and grandfathered legacy resume subscriptions allow unlimited builds and are required to upload and customize an existing PDF. The backend enforces these limits and stores build usage per account. Resume PDFs are produced from the browser print dialog using “Save as PDF.”

## ATS resume analysis

The ATS checker combines a rule-based compatibility score with an AI-estimated role match and has no monthly analysis limit. The AI assessment is an estimate, not a hiring probability or guarantee. Resume and job-description text are sent to the backend's configured AI provider; users must acknowledge this before analysis.

## Plan quotas

All plans include unlimited ATS checks. Free includes 3 mock interviews and 1 interview resume analysis per calendar month, with basic AI feedback and no company-specific questions. Pro is ₹299/month and includes 20 interviews, 5 interview resume analyses, detailed feedback, and 30 company-specific questions per month. Elite is ₹599/month and includes unlimited interviews, interview resume analyses, and company-specific questions, with detailed feedback and an improvement roadmap.
