export const LOGIN_PATH = '/login'
export const REGISTER_PATH = '/register'
export const START_PATH = '/start'
export const DASHBOARD_PATH = '/dashboard'
export const PROFILE_PATH = '/profile'
export const DISCOVERIES_PATH = '/discoveries'
export const ATS_PATH = '/ats'
export const RESUME_BUILDER_PATH = '/resume-builder'
export const ADMIN_PATH = '/admin'
export const INTERVIEW_PATH = '/interview/:interviewId'

export const getInterviewPath = (interviewId) =>
  `/interview/${encodeURIComponent(String(interviewId))}`
