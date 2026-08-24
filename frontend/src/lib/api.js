import axios from 'axios'
import { supabase } from './supabase'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      supabase.auth.signOut()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Deduplica GETs simultaneos pra mesma URL (ex: dois componentes irmaos
// pedindo os mesmos dados no mesmo mount) - o segundo reaproveita a
// requisicao em andamento do primeiro em vez de disparar outra.
const inFlightGets = new Map()

export function dedupedGet(url) {
  if (!inFlightGets.has(url)) {
    inFlightGets.set(url, api.get(url).finally(() => inFlightGets.delete(url)))
  }
  return inFlightGets.get(url)
}

export default api