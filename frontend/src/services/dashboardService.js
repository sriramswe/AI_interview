import { api, authHeaders } from './apiClient'

export async function fetchDashboardStats(token) {
  const { data } = await api.get('/users/stats', { headers: authHeaders(token) })
  return data
}

export async function fetchCompanySuggestions(token) {
  const { data } = await api.get('/interviews/companies/suggestions', {
    headers: authHeaders(token),
  })
  return data
}

export async function fetchInterviewHistory(token) {
  const { data } = await api.get('/api/interviews/history', {
    headers: authHeaders(token),
  })
  return data
}

export async function fetchInterviewAnalytics(token) {
  const { data } = await api.get('/api/interviews/analytics', {
    headers: authHeaders(token),
  })
  return data
}
