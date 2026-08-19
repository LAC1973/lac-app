import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute({ modulo, children }) {
  const { canView, loading } = useAuth()

  if (loading) return null

  if (!canView(modulo)) {
    return <Navigate to="/sem-acesso" replace />
  }

  return children
}