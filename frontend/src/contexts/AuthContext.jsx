import { createContext, useContext, useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import api from '@/lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  async function loadProfile() {
    try {
      const { data } = await api.get('/auth/me')
      setProfile(data)
    } catch {
      setProfile(null)
    }
  }

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      setUser(session?.user ?? null)
      if (session?.user) await loadProfile()
      setLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setUser(session?.user ?? null)
      if (session?.user) {
        await loadProfile()
      } else {
        setProfile(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function login(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    return data
  }

  async function logout() {
    await supabase.auth.signOut()
    setUser(null)
    setProfile(null)
  }

  function isAdmin() {
    return profile?.is_admin === true
  }

  function hasPermission(modulo, accao) {
    if (isAdmin()) return true
    if (!profile?.permissoes) return false
    const perm = profile.permissoes.find((p) => p.modulo === modulo)
    if (!perm) return false
    return perm[`pode_${accao}`] === true
  }

  function canView(modulo) {
    if (loading) return true
    return hasPermission(modulo, 'visualizar')
  }

  return (
    <AuthContext.Provider
      value={{ user, profile, loading, login, logout, isAdmin, hasPermission, canView }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}