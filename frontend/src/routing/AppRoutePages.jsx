import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import AuthPage from '../features/auth/AuthPage'
import DashboardPage, { AppHeader, DashboardHero } from '../features/dashboard/DashboardPage'
import InterviewWorkspace from '../features/interview/InterviewWorkspace'
import InterviewBriefing from '../features/interview/InterviewBriefing'
import LandingPage from '../features/landing/LandingPage'
import ProfilePage from '../features/profile/ProfilePage'
import DiscoveryDashboardPage from '../features/discovery/DiscoveryDashboardPage'
import ATSCheckerPage from '../features/ats/ATSCheckerPage'
import ResumeBuilderPage from '../features/resume/ResumeBuilderPage'
import AdminDashboardPage from '../features/admin/AdminDashboardPage'
import { useInterviewApp } from '../context/useInterviewApp'
import { ADMIN_PATH, DASHBOARD_PATH, LOGIN_PATH, RESUME_BUILDER_PATH } from './routes'
import { useRouter } from './useRouter'

function AuthRoute() {
  const { profile, token } = useInterviewApp()
  if (token && profile) return <Navigate to={DASHBOARD_PATH} replace />
  return <AuthPage />
}

function DashboardRoute() {
  const { profile, token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace />
  if (!profile) return <AuthPage />
  return <DashboardPage />
}

function ProfileRoute() {
  const { profile, token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace />
  if (!profile) return <AuthPage />
  return <ProfilePage />
}

function DiscoveriesRoute() {
  const { profile, token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace />
  if (!profile) return <AuthPage />
  return <DiscoveryDashboardPage />
}

function ATSRoute() {
  const { profile, token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace />
  if (!profile) return <AuthPage />
  return <ATSCheckerPage />
}

function ResumeBuilderRoute() {
  const { token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace state={{ from: RESUME_BUILDER_PATH }} />
  return <ResumeBuilderPage />
}

function AdminRoute() {
  const { profile, token } = useInterviewApp()
  if (!token) return <Navigate to={LOGIN_PATH} replace state={{ from: ADMIN_PATH }} />
  if (!profile) return <AuthPage />
  if (profile.role !== 'admin' && !profile.is_super_admin) {
    return <Navigate to={DASHBOARD_PATH} replace />
  }
  return <AdminDashboardPage />
}

function InterviewRoute() {
  const {
    handleBackToDashboard,
    interview,
    interviewLoadError,
    interviewLoading,
    loadSavedInterview,
    profile,
    showBriefing,
    token,
  } = useInterviewApp()
  const { interviewId } = useRouter()

  useEffect(() => {
    if (token && profile && String(interview?.id) !== interviewId) {
      loadSavedInterview(interviewId)
    }
  }, [interview?.id, interviewId, loadSavedInterview, profile, token])

  if (!token) return <Navigate to={LOGIN_PATH} replace />
  if (!profile) return <AuthPage />
  if (!interview || String(interview.id) !== interviewId) {
    return (
      <main className="page-shell">
        <AppHeader />
        <DashboardHero />
        <section aria-live="polite" className="panel interview-panel">
          {interviewLoadError ? (
            <>
              <p className="notice error" role="alert">{interviewLoadError}</p>
              <div className="answer-controls">
                <button
                  className="button secondary"
                  onClick={() => loadSavedInterview(interviewId)}
                  type="button"
                >
                  Try again
                </button>
                <button className="button primary" onClick={handleBackToDashboard} type="button">
                  Back to dashboard
                </button>
              </div>
            </>
          ) : (
            <p role="status">{interviewLoading ? 'Loading your saved interview…' : 'Opening your saved interview…'}</p>
          )}
        </section>
      </main>
    )
  }
  return (
    <main className="page-shell">
      <AppHeader />
      <DashboardHero />
      {showBriefing
        ? <InterviewBriefing />
        : <InterviewWorkspace key={interview.id} />}
      <footer className="footer-note">Your camera and microphone are accessed only after you choose to enable them.</footer>
    </main>
  )
}

function HomeRoute() {
  return <LandingPage />
}

export {
  ATSRoute,
  AdminRoute,
  AuthRoute,
  DashboardRoute,
  DiscoveriesRoute,
  HomeRoute,
  InterviewRoute,
  ProfileRoute,
  ResumeBuilderRoute,
}
