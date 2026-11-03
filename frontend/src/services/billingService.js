import { api, authHeaders } from './apiClient'

export async function createCheckout({ token, plan }) {
  const { data } = await api.post(
    '/api/billing/checkout',
    { plan },
    { headers: authHeaders(token) },
  )
  return data
}

export async function submitPaymentProof({
  token,
  plan,
  screenshot,
  transactionReference,
}) {
  const formData = new FormData()
  formData.append('plan', plan)
  formData.append('screenshot', screenshot)
  if (transactionReference?.trim()) {
    formData.append('transaction_reference', transactionReference.trim())
  }
  const { data } = await api.post('/api/billing/payments', formData, {
    headers: authHeaders(token),
  })
  return data
}

export async function fetchPaymentSubmissions(token) {
  const { data } = await api.get('/api/billing/payments', {
    headers: authHeaders(token),
  })
  return data
}
