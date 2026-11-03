import { api, authHeaders } from './apiClient'

export async function fetchCompanyDiscoveries(token) {
  const { data } = await api.get('/api/companies/discoveries', {
    headers: authHeaders(token),
  })
  return data
}

export async function startCompanyDiscovery({ token, company, jobDescription, geography }) {
  const { data } = await api.post(
    '/api/companies/discoveries',
    { company, job_description: jobDescription || null, geography: geography || null },
    { headers: authHeaders(token) },
  )
  return data
}

export async function fetchCompanyDiscoveryStatus({ token, company, geography }) {
  const { data } = await api.get('/api/companies/discoveries/status', {
    headers: authHeaders(token),
    params: { company, geography: geography || undefined },
  })
  return data
}
