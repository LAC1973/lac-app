import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import {
    LayoutDashboard, Sun, Users, PieChart, BarChart3, FileText,
  Receipt, TrendingUp, Database, DollarSign, Zap,
  Settings, SlidersHorizontal, LogOut, ChevronLeft, ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

const menuItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard, modulo: 'dashboard' },
  { path: '/usinas', label: 'Usinas', icon: Sun, modulo: 'usinas' },
  { path: '/clientes', label: 'Clientes', icon: Users, modulo: 'clientes' },
    { path: '/percentuais', label: 'Percentuais', icon: PieChart, modulo: 'percentuais' },
  { path: '/producao', label: 'Produção Diária', icon: Zap, modulo: 'producao' },
  { path: '/faturas', label: 'Faturas', icon: FileText, modulo: 'faturas' },
  { path: '/recibos', label: 'Recibos', icon: Receipt, modulo: 'recibos' },
  { path: '/rgd', label: 'RGD', icon: BarChart3, modulo: 'rgd' },
  { path: '/saldo-acm', label: 'Saldo ACM', icon: Database, modulo: 'saldo_acm' },
  { path: '/dre', label: 'DRE', icon: DollarSign, modulo: 'dre' },
  { path: '/despesas', label: 'Despesas', icon: TrendingUp, modulo: 'despesas' },
]

export default function Sidebar() {
  const { profile, isAdmin, canView, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)

  const visibleItems = menuItems.filter((item) => canView(item.modulo))

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen bg-dark-900 text-white flex flex-col z-40 transition-all duration-300',
        collapsed ? 'w-[68px]' : 'w-[260px]'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-dark-700">
        <div className="w-9 h-9 rounded-lg bg-solar-500 flex items-center justify-center shrink-0">
          <Sun size={20} className="text-dark-900" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="text-lg font-bold tracking-tight leading-none">LAC Solar</h1>
            <span className="text-[11px] text-dark-400 leading-none">Gestão de Usinas</span>
          </div>
        )}
      </div>

      {/* Menu */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-1 px-2">
          {visibleItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                    isActive
                      ? 'bg-solar-500/15 text-solar-400 font-medium'
                      : 'text-dark-400 hover:text-white hover:bg-dark-800'
                  )
                }
              >
                <item.icon size={20} className="shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Admin section */}
        {isAdmin() && (
          <>
            <div className="mx-4 my-4 border-t border-dark-700" />
            <ul className="px-2">
              <li>
                <NavLink
                  to="/funcionarios"
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-solar-500/15 text-solar-400 font-medium'
                        : 'text-dark-400 hover:text-white hover:bg-dark-800'
                    )
                  }
                >
                  <Settings size={20} className="shrink-0" />
                  {!collapsed && <span>Funcionários</span>}
                </NavLink>
              </li>
              <li>
                <NavLink
                  to="/configuracoes"
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                      isActive
                        ? 'bg-solar-500/15 text-solar-400 font-medium'
                        : 'text-dark-400 hover:text-white hover:bg-dark-800'
                    )
                  }
                >
                  <SlidersHorizontal size={20} className="shrink-0" />
                  {!collapsed && <span>Configurações</span>}
                </NavLink>
              </li>
            </ul>
          </>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-dark-700 p-3">
        {!collapsed && profile && (
          <div className="px-2 mb-3">
            <p className="text-sm font-medium truncate">{profile.full_name}</p>
            <p className="text-[11px] text-dark-400 truncate">
              {profile.is_admin ? 'Administrador' : 'Funcionário'}
            </p>
          </div>
        )}
        <div className="flex items-center gap-2">
          <button
            onClick={logout}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-dark-400 hover:text-red-400 hover:bg-dark-800 transition-colors flex-1"
          >
            <LogOut size={18} />
            {!collapsed && <span>Sair</span>}
          </button>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-800 transition-colors"
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
      </div>
    </aside>
  )
}