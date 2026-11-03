import { api, authHeaders } from './apiClient'

export async function fetchAdminSummary(token) {
  const { data } = await api.get('/api/admin/summary', {
    headers: authHeaders(token),
  })
  return data
}

export async function fetchAdminUsers({ token, search = '', offset = 0, limit = 50 }) {
  const { data } = await api.get('/api/admin/users', {
    headers: authHeaders(token),
    params: { search, offset, limit },
  })
  return data
}

export async function updateAdminUser({ token, userId, updates }) {
  const { data } = await api.patch(`/api/admin/users/${userId}`, updates, {
    headers: authHeaders(token),
  })
  return data
}

export async function deleteAdminUser({ token, userId }) {
  await api.delete(`/api/admin/users/${userId}`, {
    headers: authHeaders(token),
  })
}

export async function fetchPendingPayments(token) {
  const { data } = await api.get('/api/admin/payments/pending', {
    headers: authHeaders(token),
  })
  return data
}

export async function fetchPaymentReceipt({ token, paymentId }) {
  const { data } = await api.get(`/api/admin/payments/${paymentId}/receipt`, {
    headers: authHeaders(token),
    responseType: 'blob',
  })
  return data
}

export async function reviewPayment({ token, paymentId, decision, reviewNote }) {
  const { data } = await api.post(
    `/api/admin/payments/${paymentId}/review`,
    { decision, review_note: reviewNote },
    { headers: authHeaders(token) },
  )
  return data
}
