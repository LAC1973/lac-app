import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import Sidebar from './Sidebar'

export default function DashboardLayout() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-dark-100">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-solar-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-dark-500">Carregando...</span>
        </div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-[260px] p-6 transition-all duration-300">
        <Outlet />
      </main>
    </div>
  )
}