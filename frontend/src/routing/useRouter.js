import { matchPath, useLocation, useNavigate } from 'react-router-dom'
import { INTERVIEW_PATH } from './routes'

export function useRouter() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const interviewMatch = matchPath(INTERVIEW_PATH, pathname)

  return {
    navigate,
    pathname,
    interviewId: interviewMatch?.params.interviewId ?? null,
  }
}