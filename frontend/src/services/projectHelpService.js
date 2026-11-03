import { api, authHeaders } from './apiClient'

export async function askProjectHelp({ token, message, history }) {
  const { data } = await api.post(
    '/api/chat/project',
    { message, history },
    { headers: authHeaders(token) },
  )
  return data.answer
}
