import { api, authHeaders } from './apiClient'

function createResumeFormData({ file, resumeText, aiProcessingAcknowledged }) {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  if (resumeText) {
    formData.append('resume_text', resumeText)
  }
  formData.append('ai_processing_acknowledged', String(aiProcessingAcknowledged))
  return formData
}

export async function generateTargetJobDescription({
  file,
  resumeText,
  aiProcessingAcknowledged,
  token,
}) {
  const formData = createResumeFormData({
    file,
    resumeText,
    aiProcessingAcknowledged,
  })
  const headers = token ? authHeaders(token) : {}
  const { data } = await api.post('/api/ats/generate-target', formData, {
    headers,
  })
  return data
}

export async function analyzeAtsScore({
  file,
  resumeText,
  jobDescription,
  targetRole,
  aiProcessingAcknowledged,
  token,
}) {
  const formData = createResumeFormData({
    file,
    resumeText,
    aiProcessingAcknowledged,
  })
  if (jobDescription) {
    formData.append('job_description', jobDescription)
  }
  if (targetRole) {
    formData.append('target_role', targetRole)
  }

  const headers = token ? authHeaders(token) : {}
  const { data } = await api.post('/api/ats/analyze', formData, {
    headers,
  })
  return data
}
