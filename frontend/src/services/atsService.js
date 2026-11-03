import { api, authHeaders } from './apiClient'

export async function analyzeAtsScore({
  file,
  resumeText,
  jobDescription,
  targetRole,
  token,
}) {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  }
  if (resumeText) {
    formData.append('resume_text', resumeText)
  }
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

