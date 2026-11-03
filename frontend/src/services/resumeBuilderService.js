import { api, authHeaders } from './apiClient'

export async function fetchResumeBuilderData(token) {
  const { data } = await api.get('/api/resumes', {
    headers: authHeaders(token),
  })
  return data
}

export async function importResumeForCustomization({ token, file }) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/api/resumes/import', formData, {
    headers: authHeaders(token),
  })
  return data
}

export async function createResume({ token, resume }) {
  const { data } = await api.post('/api/resumes', resume, {
    headers: authHeaders(token),
  })
  return data
}

export async function updateResume({ token, resumeId, resume }) {
  const { data } = await api.put(`/api/resumes/${resumeId}`, resume, {
    headers: authHeaders(token),
  })
  return data
}
