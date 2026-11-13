import { api, authHeaders } from './apiClient'

export async function fetchInterviewRounds({ token, role, jobDescription }) {
  const { data } = await api.get('/api/interviews/rounds', {
    headers: authHeaders(token),
    params: {
      role,
      job_description: jobDescription || undefined,
    },
  })
  return data
}

export async function startInterview({
  token,
  role,
  subRole,
  company,
  geography,
  jobDescription,
  difficultyLevel,
  questionsPerRound = 20,
  technicalCategories = [],
  interviewerName,
  isPanel,
  resumeFile,
  onUploadProgress,
}) {
  const headers = authHeaders(token)
  let response
  if (resumeFile) {
    const formData = new FormData()
    formData.append('file', resumeFile)
    formData.append('role_category', role)
    formData.append('sub_role', subRole || role)
    formData.append('difficulty_level', String(difficultyLevel))
    formData.append('questions_per_round', String(questionsPerRound))
    formData.append('target_company', company || '')
    formData.append('target_geography', geography || '')
    formData.append('job_description', jobDescription || '')
    formData.append('interviewer_name', interviewerName)
    formData.append('is_panel', String(isPanel))
    technicalCategories.forEach((category) => {
      formData.append('technical_categories', category)
    })
    response = await api.post('/interviews/upload-resume', formData, {
      headers,
      onUploadProgress: (event) => {
        if (event.total) onUploadProgress?.(event.loaded / event.total)
      },
    })
  } else {
    response = await api.post('/interviews/start', {
      role_category: role,
      sub_role: subRole || role,
      difficulty_level: difficultyLevel,
      questions_per_round: questionsPerRound,
      target_company: company || null,
      target_geography: geography || null,
      job_description: jobDescription || null,
      interviewer_name: interviewerName,
      is_panel: isPanel,
      technical_categories: technicalCategories,
    }, { headers })
  }
  const { data } = response
  return data
}

export async function fetchInterviewHistoryDetail({ token, interviewId }) {
  const { data } = await api.get(`/api/interviews/history/${interviewId}`, {
    headers: authHeaders(token),
  })
  return data
}

export async function retryInterviewAnswer({ token, interviewId, answerId, answer }) {
  const { data } = await api.post(
    `/api/interviews/history/${interviewId}/answers/${answerId}/retry`,
    { answer: answer.trim() },
    { headers: authHeaders(token) },
  )
  return data
}

export async function deleteSavedInterviewAnswer({ token, interviewId, answerId }) {
  await api.delete(
    `/api/interviews/history/${interviewId}/answers/${answerId}`,
    { headers: authHeaders(token) },
  )
}

export async function deletePendingInterviewAnswer({ token, interviewId }) {
  await api.delete(
    `/api/interviews/history/${interviewId}/pending-answer`,
    { headers: authHeaders(token) },
  )
}

export async function submitInterviewAnswer({ token, interviewId, answer, durationSeconds }) {
  const { data } = await api.post('/interviews/submit-answer', {
    interview_id: interviewId,
    answer: answer.trim(),
    answer_duration_seconds: durationSeconds || undefined,
  }, { headers: authHeaders(token) })
  return data
}

export async function generateLearningRoadmap({ token, interviewId, signal }) {
  const { data } = await api.post(
    `/api/interviews/history/${interviewId}/learning-roadmap`,
    {},
    { headers: authHeaders(token), signal },
  )
  return data
}

export async function fetchCodingLedger({ token, interviewId }) {
  const { data } = await api.get(
    `/api/interviews/${interviewId}/coding/ledger`,
    { headers: authHeaders(token) },
  )
  return data
}

export async function startCodingProblem({ token, interviewId, language }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/problem`,
    { language },
    { headers: authHeaders(token) },
  )
  return data
}

export async function requestCodingHint({ token, interviewId }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/hint`,
    {},
    { headers: authHeaders(token) },
  )
  return data
}

export async function submitCodingSolution({ token, interviewId, code, explanation }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/submit`,
    { code, explanation },
    { headers: authHeaders(token) },
  )
  return data
}

export async function generateCodingRoadmap({ token, interviewId, signal }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/roadmap`,
    {},
    { headers: authHeaders(token), signal },
  )
  return data
}

export async function completeCodingRoadmap({ token, interviewId }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/roadmap/complete`,
    {},
    { headers: authHeaders(token) },
  )
  return data
}

export async function retryCodingProblem({ token, interviewId }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/retry`,
    {},
    { headers: authHeaders(token) },
  )
  return data
}

export async function advanceCodingRound({ token, interviewId }) {
  const { data } = await api.post(
    `/api/interviews/${interviewId}/coding/next`,
    {},
    { headers: authHeaders(token) },
  )
  return data
}
