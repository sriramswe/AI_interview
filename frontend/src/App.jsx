import { Route, Routes } from 'react-router-dom'
import ProjectHelpChat from './features/chat/ProjectHelpChat'
import { useInterviewApp } from './context/useInterviewApp'
import {
  AdminRoute,
  ATSRoute,
  AuthRoute,
  DashboardRoute,
  DiscoveriesRoute,
  HomeRoute,
  InterviewRoute,
  ProfileRoute,
  ResumeBuilderRoute,
} from './routing/AppRoutePages'
import {
  ATS_PATH,
  ADMIN_PATH,
  DASHBOARD_PATH,
  DISCOVERIES_PATH,
  INTERVIEW_PATH,
  LOGIN_PATH,
  PROFILE_PATH,
  REGISTER_PATH,
  RESUME_BUILDER_PATH,
  START_PATH,
} from './routing/routes'
import CandidateOnboardingPage from './features/onboarding/CandidateOnboardingPage'

export default function App() {
  const { profile, token } = useInterviewApp()
  return (
    <>
      <Routes>
        <Route path={LOGIN_PATH} element={<AuthRoute />} />
        <Route path={REGISTER_PATH} element={<AuthRoute />} />
        <Route path={START_PATH} element={<CandidateOnboardingPage />} />
        <Route path={DASHBOARD_PATH} element={<DashboardRoute />} />
        <Route path={PROFILE_PATH} element={<ProfileRoute />} />
        <Route path={DISCOVERIES_PATH} element={<DiscoveriesRoute />} />
        <Route path={ATS_PATH} element={<ATSRoute />} />
        <Route path={RESUME_BUILDER_PATH} element={<ResumeBuilderRoute />} />
        <Route path={ADMIN_PATH} element={<AdminRoute />} />
        <Route path={INTERVIEW_PATH} element={<InterviewRoute />} />
        <Route path="/" element={<HomeRoute />} />
        <Route path="*" element={<HomeRoute />} />
      </Routes>
      {token && profile && <ProjectHelpChat />}
    </>
  )
}
