import { api, authHeaders } from './apiClient'

export async function authenticate({ mode, form }) {
  const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register'
  const { data } = await api.post(endpoint, form)
  return data
}

export async function authenticateWithGoogle(credential) {
  const { data } = await api.post('/auth/google', { token: credential })
  return data
}

export async function fetchAccount(token) {
  const headers = authHeaders(token)
  const [profile, subscription, candidateProfile] = await Promise.all([
    api.get('/api/users/me', { headers }),
    api.get('/api/billing/subscription', { headers }),
    api.get('/api/users/me/candidate-profile', { headers }),
  ])
  return {
    profile: profile.data,
    subscription: subscription.data,
    candidateProfile: candidateProfile.data,
  }
}

export async function saveCandidateProfile({ token, candidateProfile }) {
  const { data } = await api.put(
    '/api/users/me/candidate-profile',
    candidateProfile,
    { headers: authHeaders(token) },
  )
  return data
}

export async function updateProfile({ token, username, email, gender }) {
  const { data } = await api.patch(
    '/api/users/me',
    { username, email, gender },
    { headers: authHeaders(token) },
  )
  return data
}

export async function changePassword({ token, currentPassword, newPassword }) {
  const { data } = await api.post(
    '/api/users/me/password',
    { current_password: currentPassword, new_password: newPassword },
    { headers: authHeaders(token) },
  )
  return data
}

export async function logout(token) {
  return api.post('/api/auth/logout', {}, { headers: authHeaders(token) })
}
