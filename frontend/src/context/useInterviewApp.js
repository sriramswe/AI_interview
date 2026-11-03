import { useContext } from 'react'
import { InterviewAppContext } from './interviewAppContextValue'

export function useInterviewApp() {
  const context = useContext(InterviewAppContext)
  if (!context) {
    throw new Error('useInterviewApp must be used within InterviewAppProvider')
  }
  return context
}
