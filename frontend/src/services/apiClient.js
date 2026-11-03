import axios from 'axios'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'
).replace(/\/+$/, '')
export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

export const api = axios.create({ baseURL: API_BASE_URL })

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestHeaders = error.config?.headers
    const authorization = requestHeaders?.get?.('Authorization')
      || requestHeaders?.Authorization
      || requestHeaders?.authorization
    if (error.response?.status === 401 && authorization && typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('interviewai:authentication-expired'))
    }
    return Promise.reject(error)
  },
)

export function authHeaders(token) {
  return { Authorization: `Bearer ${token}` }
}

export function getApiError(error, fallback) {
  if (API_BASE_URL.includes('your-backend.example.com')) {
    return 'The backend URL is still a placeholder. Set VITE_API_BASE_URL to your running backend URL.'
  }
  return error.response?.data?.detail || fallback
}
