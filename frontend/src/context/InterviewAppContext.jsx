import { useCallback, useEffect, useRef, useState } from 'react'
import { InterviewAppContext } from './interviewAppContextValue'
import { useRouter } from '../routing/useRouter'
import {
  DASHBOARD_PATH,
  getInterviewPath,
  LOGIN_PATH,
  REGISTER_PATH,
} from '../routing/routes'
import { downloadCalendarInvite } from '../features/scheduling/calendarInvite'
import { getApiError } from '../services/apiClient'
import {
  authenticate,
  authenticateWithGoogle,
  fetchAccount,
  logout as logoutAccount,
  saveCandidateProfile,
  updateProfile,
} from '../services/authService'
import {
  deletePendingInterviewAnswer,
  fetchInterviewHistoryDetail,
  fetchInterviewRounds,
  generateLearningRoadmap,
  startInterview as createInterview,
  submitInterviewAnswer,
} from '../services/interviewService'
import {
  createCheckout as requestCheckout,
  fetchPaymentSubmissions,
  submitPaymentProof,
} from '../services/billingService'
import { fetchCompanySuggestions, fetchDashboardStats } from '../services/dashboardService'

export function InterviewAppProvider({ children }) {
  const { navigate, pathname } = useRouter()
  const [token, setToken] = useState(() => localStorage.getItem('access_token') || '')
  const [profile, setProfile] = useState(null)
  const [candidateProfile, setCandidateProfile] = useState(null)
  const [authForm, setAuthForm] = useState({
    username: '',
    email: '',
    password: '',
    gender: '',
  })
  const [authError, setAuthError] = useState('')
  const [role, setRole] = useState('Software Engineer')
  const [subRole, setSubRole] = useState('Software Engineer')
  const [company, setCompany] = useState('')
  const [geography, setGeography] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [difficultyLevel, setDifficultyLevel] = useState(2)
  const [questionsPerRound, setQuestionsPerRound] = useState(20)
  const [technicalCategories, setTechnicalCategories] = useState([])
  const [interviewerName, setInterviewerName] = useState('Adinath')
  const [isPanel, setIsPanel] = useState(false)
  const [resumeFile, setResumeFile] = useState(null)
  const [interviewProgress, setInterviewProgress] = useState(null)
  const [rounds, setRounds] = useState([])
  const [stats, setStats] = useState({ total_interviews: 0, avg_score: 0 })
  const [companySuggestions, setCompanySuggestions] = useState([])
  const [interview, setInterview] = useState(null)
  const [interviewLoading, setInterviewLoading] = useState(false)
  const [interviewLoadError, setInterviewLoadError] = useState('')
  const [showBriefing, setShowBriefing] = useState(false)
  const [lastEvaluation, setLastEvaluation] = useState(null)
  const [subscription, setSubscription] = useState(null)
  const [checkout, setCheckout] = useState(null)
  const [paymentFile, setPaymentFile] = useState(null)
  const [paymentReference, setPaymentReference] = useState('')
  const [paymentSubmissions, setPaymentSubmissions] = useState([])
  const [paymentStatus, setPaymentStatus] = useState('')
  const [busy, setBusy] = useState(false)
  const answerSubmissionInProgress = useRef(false)
  const [scheduleTime, setScheduleTime] = useState('')
  const authMode = pathname === REGISTER_PATH ? 'register' : 'login'

  const clearToken = useCallback(() => {
    localStorage.removeItem('access_token')
    setToken('')
    setProfile(null)
    setInterview(null)
    setInterviewLoadError('')
    setSubscription(null)
    setCheckout(null)
  }, [])

  useEffect(() => {
    const handleExpiredAuthentication = () => {
      if (!token) return
      clearToken()
      setAuthError('Your sign-in expired. Please sign in again; your saved interview progress is safe.')
      navigate(LOGIN_PATH, { replace: true })
    }

    window.addEventListener(
      'interviewai:authentication-expired',
      handleExpiredAuthentication,
    )
    return () => window.removeEventListener(
      'interviewai:authentication-expired',
      handleExpiredAuthentication,
    )
  }, [clearToken, navigate, token])

  useEffect(() => {
    if (!token) return undefined
    let active = true
    const loadAccount = async () => {
      try {
        const account = await fetchAccount(token)
        if (!active) return
        setProfile(account.profile)
        setSubscription(account.subscription)
        setCandidateProfile(account.candidateProfile)
        setAuthError('')
      } catch (error) {
        if (!active) return
        if (error.response?.status === 401) clearToken()
        else setAuthError(getApiError(error, 'Could not load your account.'))
      }
    }
    loadAccount()
    return () => {
      active = false
    }
  }, [clearToken, token])

  useEffect(() => {
    if (!token) return undefined
    let active = true
    const loadDashboardData = async () => {
      const results = await Promise.allSettled([
        fetchDashboardStats(token),
        fetchCompanySuggestions(token),
        fetchPaymentSubmissions(token),
      ])
      if (!active) return
      const [statsResult, suggestionsResult, paymentsResult] = results
      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value)
      } else {
        setPaymentStatus(getApiError(statsResult.reason, 'Could not load interview stats.'))
      }
      if (suggestionsResult.status === 'fulfilled') {
        setCompanySuggestions(suggestionsResult.value)
      } else {
        setPaymentStatus(getApiError(suggestionsResult.reason, 'Could not load company suggestions.'))
      }
      if (paymentsResult.status === 'fulfilled') {
        setPaymentSubmissions(paymentsResult.value)
      } else {
        setPaymentStatus(getApiError(paymentsResult.reason, 'Could not load payment history.'))
      }
    }
    loadDashboardData()
    return () => {
      active = false
    }
  }, [token])

  const acceptAuthentication = useCallback(async (data) => {
    localStorage.setItem('access_token', data.access_token)
    setToken(data.access_token)
    setProfile(data.user)
    setAuthForm({ username: '', email: '', password: '', gender: '' })
    setAuthError('')
    const savedDraft = localStorage.getItem('interview_setup_draft')
    if (savedDraft) {
      try {
        const draft = JSON.parse(savedDraft)
        if (draft.candidateProfile) {
          setRole(draft.role || 'Software Engineer')
          setSubRole(draft.subRole || draft.role || 'Software Engineer')
          setCandidateProfile(draft.candidateProfile)
          await saveCandidateProfile({
            token: data.access_token,
            candidateProfile: draft.candidateProfile,
          })
          if (['pro', 'elite'].includes(draft.accessPlan)) {
            try {
              const checkoutData = await requestCheckout({
                token: data.access_token,
                plan: draft.accessPlan,
              })
              setCheckout(checkoutData)
              setPaymentStatus('Complete the payment steps below; your selected plan activates after review.')
            } catch (error) {
              setPaymentStatus(getApiError(error, 'Could not start checkout. Choose a plan from the dashboard to try again.'))
            }
          }
          localStorage.removeItem('interview_setup_draft')
        } else {
          throw new Error('Your saved interview setup is incomplete. Please start the setup again.')
        }
      } catch (error) {
        setPaymentStatus(error instanceof SyntaxError
          ? 'Your saved interview setup could not be read. You can continue by setting up an interview on the dashboard.'
          : error.message || 'Could not save your candidate profile.')
        if (error instanceof SyntaxError) localStorage.removeItem('interview_setup_draft')
      }
    }
    navigate(DASHBOARD_PATH, { replace: true })
  }, [navigate])

  const handleAuthSubmit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setAuthError('')
    try {
      const data = await authenticate({ mode: authMode, form: authForm })
      await acceptAuthentication(data)
    } catch (error) {
      setAuthError(getApiError(error, 'Could not authenticate. Try again.'))
    } finally {
      setBusy(false)
    }
  }

  const handleGoogleCredential = useCallback(async (credential, errorMessage) => {
    if (!credential) {
      if (errorMessage) setAuthError(errorMessage)
      return
    }
    setBusy(true)
    setAuthError('')
    try {
      const data = await authenticateWithGoogle(credential)
      await acceptAuthentication(data)
    } catch (error) {
      setAuthError(getApiError(error, 'Google sign-in failed.'))
    } finally {
      setBusy(false)
    }
  }, [acceptAuthentication])

  const handleProfileUpdate = async (updates) => {
    setBusy(true)
    setPaymentStatus('')
    try {
      const updatedProfile = await updateProfile({ token, ...updates })
      setProfile(updatedProfile)
      setPaymentStatus('Profile updated.')
      return true
    } catch (error) {
      setPaymentStatus(getApiError(error, 'Could not update your profile.'))
      return false
    } finally {
      setBusy(false)
    }
  }

  const changeAuthMode = () => {
    const nextMode = authMode === 'login' ? 'register' : 'login'
    navigate(nextMode === 'register' ? REGISTER_PATH : LOGIN_PATH)
    setAuthError('')
  }

  const handleHome = () => {
    setInterview(null)
    setShowBriefing(false)
    setLastEvaluation(null)
    setRounds([])
  }

  const handleLogout = async () => {
    try {
      await logoutAccount(token)
    } catch {
      // Clear the local credential even when the session is already unavailable.
    } finally {
      clearToken()
      navigate(LOGIN_PATH, { replace: true })
    }
  }

  const loadRounds = async () => {
    try {
      const data = await fetchInterviewRounds({ token, role, jobDescription })
      setRounds(data)
      return true
    } catch (error) {
      setRounds([])
      setPaymentStatus(getApiError(error, 'Could not load interview rounds.'))
      return false
    }
  }

  const handleStartInterview = async (event) => {
    event.preventDefault()
    const currentPlan = subscription?.plan || 'free'
    if (jobDescription.trim() && currentPlan === 'free') {
      setPaymentStatus('A Pro plan is required to tailor an interview with a job description. Upgrade or clear the job description to continue.')
      return
    }
    if (isPanel && currentPlan !== 'elite') {
      setPaymentStatus('An Elite plan is required for panel interviews. Upgrade or turn off panel mode to continue.')
      return
    }
    if (resumeFile && !resumeFile.name.toLowerCase().endsWith('.pdf')) {
      setPaymentStatus('Upload your resume as a PDF file.')
      return
    }
    setBusy(true)
    setPaymentStatus('')
    setInterviewLoadError('')
    setInterviewProgress(resumeFile ? { stage: 'uploading', percent: 0 } : null)
    let scanTimer
    try {
      const data = await createInterview({
        token,
        role,
        subRole,
        company,
        geography,
        jobDescription,
        difficultyLevel,
        questionsPerRound,
        technicalCategories,
        interviewerName,
        isPanel,
        resumeFile,
        onUploadProgress: (progress) => {
          if (progress >= 1) {
            setInterviewProgress({ stage: 'scanning', percent: 100 })
            window.clearTimeout(scanTimer)
            scanTimer = window.setTimeout(() => {
              setInterviewProgress((current) => (
                current?.stage === 'scanning'
                  ? { stage: 'preparing', percent: 100 }
                  : current
              ))
            }, 1200)
            return
          }
          setInterviewProgress({
            stage: 'uploading',
            percent: Math.min(99, Math.round(progress * 100)),
          })
        },
      })
      window.clearTimeout(scanTimer)
      setInterviewProgress(null)
      setInterview(data)
      setShowBriefing(Boolean(data.company_intelligence))
      setLastEvaluation(null)
      setRounds([])
      navigate(getInterviewPath(data.id))
    } catch (error) {
      window.clearTimeout(scanTimer)
      if (resumeFile) setInterviewProgress({ stage: 'failed', percent: 100 })
      setPaymentStatus(getApiError(error, 'Could not start the interview.'))
    } finally {
      setBusy(false)
    }
  }

  const handleResumeFileChange = (file) => {
    setResumeFile(file)
    setInterviewProgress(null)
    setPaymentStatus('')
  }

  const handleSubmitAnswer = async (answer, durationSeconds) => {
    if (
      !answer.trim()
      || !interview
      || answerSubmissionInProgress.current
    ) return false
    answerSubmissionInProgress.current = true
    setBusy(true)
    setPaymentStatus('')
    try {
      const data = await submitInterviewAnswer({
        token,
        interviewId: interview.id,
        answer,
        durationSeconds,
      })
      setLastEvaluation(data.evaluation)
      setInterview((current) => ({
        ...current,
        first_question: data.next_question,
        question_category: data.question_category,
        interview_round: data.current_round || data.next_round || current.interview_round,
        current_round_number: data.current_round_number
          ?? data.next_round_number
          ?? current.current_round_number,
        technical_category_plan: current.technical_category_plan,
        pending_answer: null,
        finished: data.interview_completed || data.terminated,
        overall_status: data.overall_status ?? (
          data.interview_completed || data.terminated
            ? (data.round_passed ? 'completed' : 'failed')
            : 'in_progress'
        ),
        overall_message: data.overall_message,
        failed_round: data.failed_round,
        round_completed: data.round_completed,
        round_passed: data.round_passed,
        round_scores: data.round_scores,
        rounds_completed: data.rounds_completed,
        master_report: data.master_report,
        master_report_pending: Boolean(data.master_report_pending),
        final_answer: data.master_report_pending ? answer : null,
        ai_provider_status: data.ai_provider_status || null,
        report_provider_status: data.report_provider_status ?? current.report_provider_status,
        round_score: data.round_score,
        questions_asked: data.questions_asked ?? current.questions_asked,
        total_questions: data.total_questions ?? current.total_questions,
        questions_per_round: data.questions_per_round ?? current.questions_per_round,
        coding_gate_required: data.coding_gate_required ?? false,
        difficulty_level: data.difficulty_level ?? current.difficulty_level,
        difficulty_scaled: data.difficulty_scaled || false,
      }))
      return true
    } catch (error) {
      const submitError = getApiError(error, 'Could not submit your answer.')
      setPaymentStatus(submitError)
      try {
        const saved = await fetchInterviewHistoryDetail({
          token,
          interviewId: interview.id,
        })
        const transcript = Array.isArray(saved.transcript) ? saved.transcript : []
        const lastTurn = transcript[transcript.length - 1]
        const pendingAnswer = (
          lastTurn?.role === 'user'
          && lastTurn.evaluation_pending === true
          && typeof lastTurn.content === 'string'
        ) ? lastTurn.content : null
        setInterview((current) => (
          current?.id === interview.id
            ? { ...current, pending_answer: pendingAnswer }
            : current
        ))
      } catch (historyError) {
        setPaymentStatus(
          `${submitError} ${getApiError(
            historyError,
            'Could not verify whether the answer is still awaiting evaluation.',
          )}`,
        )
      }
      return false
    } finally {
      answerSubmissionInProgress.current = false
      setBusy(false)
    }
  }

  const handleDeletePendingAnswer = async (interviewId) => {
    try {
      await deletePendingInterviewAnswer({ token, interviewId })
      setInterview((current) => (
        current?.id === interviewId
          ? { ...current, pending_answer: null }
          : current
      ))
      setPaymentStatus('')
      return true
    } catch (error) {
      setPaymentStatus(getApiError(error, 'Could not delete your saved answer.'))
      return false
    }
  }

  const loadSavedInterview = useCallback(async (interviewId) => {
    if (!token) return
    setInterviewLoading(true)
    setInterviewLoadError('')
    try {
      const saved = await fetchInterviewHistoryDetail({ token, interviewId })
      const transcript = Array.isArray(saved.transcript) ? saved.transcript : []
      const currentQuestion = [...transcript]
        .reverse()
        .find((item) => item?.role === 'assistant' && typeof item.content === 'string')
      const lastAnsweredTurn = [...transcript]
        .reverse()
        .find((item) => item?.role === 'user' && item.evaluation)
      const completionTurn = [...transcript]
        .reverse()
        .find((item) => item?.role === 'user' && item.completion)
      const finalAnswerTurn = [...transcript]
        .reverse()
        .find((item) => item?.role === 'user' && item.master_report)
      const pendingFinalReport = [...transcript]
        .reverse()
        .find((item) => item?.role === 'user' && item.report_pending)
      const pendingAnswer = [...transcript]
        .reverse()
        .find((item) => item?.role === 'user' && item.evaluation_pending === true)
      const firstTurn = transcript.find((item) => item?.role === 'assistant')

      setInterview({
        id: saved.session_id,
        role_category: saved.role,
        sub_role: saved.sub_role,
        difficulty: saved.difficulty,
        difficulty_level: saved.difficulty_level,
        target_company: saved.target_company,
        target_geography: firstTurn?.target_geography || '',
        interviewer_name: saved.interviewer_name || 'Adinath',
        is_panel: Boolean(saved.is_panel),
        interview_round: saved.interview_round,
        questions_asked: saved.questions_asked || 0,
        total_questions: saved.total_questions || 0,
        questions_per_round: saved.questions_per_round || 20,
        question_category: currentQuestion?.technical_category || null,
        technical_category_plan: transcript.find((item) => item?.role === 'system')
          ?.technical_category_plan || [],
        coding_gate_required: saved.coding_gate_required || false,
        pending_answer: pendingAnswer?.content || null,
        first_question: currentQuestion?.content || 'Interview complete',
        finished: saved.status !== 'in_progress',
        overall_status: saved.status,
        overall_message: completionTurn?.completion?.message || (
          pendingFinalReport
            ? 'All interview rounds are complete. The final scorecard could not be generated yet; retry the scorecard when ready.'
            : ''
        ),
        failed_round: completionTurn?.completion?.failed_round || null,
        round_completed: false,
        round_scores: saved.round_scores || {},
        rounds_completed: saved.rounds_completed || [],
        master_report: finalAnswerTurn?.master_report || null,
        master_report_pending: Boolean(pendingFinalReport),
        final_answer: pendingFinalReport?.content || null,
        ai_provider_status: lastAnsweredTurn?.ai_provider_status || null,
        report_provider_status: finalAnswerTurn?.report_provider_status || null,
      })
      setLastEvaluation(lastAnsweredTurn?.evaluation || null)
      setShowBriefing(false)
      setRounds([])
      setPaymentStatus('')
    } catch (error) {
      setInterviewLoadError(getApiError(error, 'Could not reopen this interview session.'))
    } finally {
      setInterviewLoading(false)
    }
  }, [token])

  const handleGenerateRoadmap = async () => {
    try {
      const data = await generateLearningRoadmap({ token, interviewId: interview.id })
      setPaymentStatus(JSON.stringify(data, null, 2))
    } catch (error) {
      setPaymentStatus(getApiError(error, 'Could not create a learning roadmap.'))
    }
  }

  const handleCreateCheckout = async (plan) => {
    setBusy(true)
    setPaymentStatus('')
    try {
      const data = await requestCheckout({ token, plan })
      setCheckout(data)
    } catch (error) {
      setPaymentStatus(getApiError(error, 'Could not create UPI checkout.'))
    } finally {
      setBusy(false)
    }
  }

  const handlePaymentProofSubmit = async (event) => {
    event.preventDefault()
    if (!checkout || !paymentFile) {
      setPaymentStatus('Choose the payment screenshot before submitting it.')
      return
    }
    setBusy(true)
    try {
      const data = await submitPaymentProof({
        token,
        plan: checkout.plan,
        screenshot: paymentFile,
        transactionReference: paymentReference,
      })
      setPaymentStatus(`Payment proof submitted for review (reference #${data.payment_id}).`)
      setPaymentSubmissions((current) => [{
        ...data,
        review_note: null,
        reviewed_at: null,
      }, ...current])
      setPaymentFile(null)
      setPaymentReference('')
      setCheckout(null)
    } catch (error) {
      setPaymentStatus(getApiError(error, 'Could not upload payment proof.'))
    } finally {
      setBusy(false)
    }
  }

  const handleCreateCalendarInvite = () => {
    try {
      downloadCalendarInvite({ scheduleTime, role })
      setPaymentStatus('')
    } catch (error) {
      setPaymentStatus(error.message)
    }
  }

  const handleBackToDashboard = () => {
    setInterview(null)
    setShowBriefing(false)
    setLastEvaluation(null)
    setInterviewLoadError('')
    setRounds([])
    navigate(DASHBOARD_PATH, { replace: true })
  }

  const handleEnterInterview = () => setShowBriefing(false)
  const handleCodingStageComplete = () => {
    setInterview((current) => current
      ? { ...current, coding_gate_required: false }
      : current)
  }

  const value = {
    authError,
    authForm,
    authMode,
    busy,
    changeAuthMode,
    checkout,
    company,
    geography,
    companySuggestions,
    difficultyLevel,
    handleDifficultyChange: (value) => setDifficultyLevel(Number(value)),
    handleQuestionsPerRoundChange: (value) => setQuestionsPerRound(Number(value)),
    handleTechnicalCategoriesChange: setTechnicalCategories,
    handleEnterInterview,
    handleInterviewerChange: setInterviewerName,
    handlePanelChange: setIsPanel,
    handleProfileUpdate,
    handleResumeFileChange,
    handleAuthChange: (field, value) => setAuthForm((current) => ({ ...current, [field]: value })),
    handleAuthSubmit,
    handleBackToDashboard,
    handleCompanyChange: setCompany,
    handleGeographyChange: setGeography,
    handleCreateCalendarInvite,
    handleCreateCheckout,
    handleCodingStageComplete,
    handleDeletePendingAnswer,
    handleGenerateRoadmap,
    handleGoogleCredential,
    handleHome,
    handleJobDescriptionChange: setJobDescription,
    handleLoadRounds: loadRounds,
    loadSavedInterview,
    handleLogout,
    handlePaymentFileChange: setPaymentFile,
    handlePaymentProofSubmit,
    handlePaymentReferenceChange: setPaymentReference,
    paymentReference,
    paymentSubmissions,
    handleRoleChange: setRole,
    handleScheduleTimeChange: setScheduleTime,
    handleStartInterview,
    handleSubRoleChange: setSubRole,
    handleSubmitAnswer,
    interview,
    interviewLoading,
    interviewLoadError,
    interviewProgress,
    interviewerName,
    isPanel,
    jobDescription,
    lastEvaluation,
    paymentFile,
    paymentStatus,
    questionsPerRound,
    profile,
    candidateProfile,
    role,
    rounds,
    resumeFile,
    scheduleTime,
    subRole,
    technicalCategories,
    subscription,
    showBriefing,
    stats,
    token,
  }

  return (
    <InterviewAppContext.Provider value={value}>
      {children}
    </InterviewAppContext.Provider>
  )
}
