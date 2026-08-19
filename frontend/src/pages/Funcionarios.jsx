import { useState, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import {
  Plus, UserCog, ToggleLeft, ToggleRight, KeyRound,
  X, Check, ChevronDown, ChevronUp, Shield,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const MODULOS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'usinas', label: 'Usinas' },
  { key: 'clientes', label: 'Clientes' },
  { key: 'percentuais', label: 'Percentuais' },
  { key: 'producao', label: 'Produção Diária' },
  { key: 'faturas', label: 'Faturas' },
  { key: 'recibos', label: 'Recibos' },
  { key: 'rgd', label: 'RGD' },
  { key: 'saldo_acm', label: 'Saldo ACM' },
  { key: 'dre', label: 'DRE' },
  { key: 'despesas', label: 'Despesas' },
]

const ACOES = [
  { key: 'pode_visualizar', label: 'Visualizar' },
  { key: 'pode_criar', label: 'Criar' },
  { key: 'pode_editar', label: 'Editar' },
  { key: 'pode_excluir', label: 'Excluir' },
]

export default function Funcionarios() {
  const { isAdmin } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [expandedUser, setExpandedUser] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showResetPassword, setShowResetPassword] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '' })

  if (!isAdmin()) return <Navigate to="/" replace />

  useEffect(() => { loadUsers() }, [])

  async function loadUsers() {
    setLoading(true)
    try {
      const { data } = await api.get('/users/')
      setUsers(data)
    } catch (err) {
      console.error('Erro ao carregar usuários:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateUser(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/users/', {
        ...form,
        permissoes: MODULOS.map((m) => ({
          modulo: m.key,
          pode_visualizar: false,
          pode_criar: false,
          pode_editar: false,
          pode_excluir: false,
        })),
      })
      setShowForm(false)
      setForm({ email: '', password: '', full_name: '', phone: '' })
      await loadUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao criar funcionário')
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleActive(userId) {
    try {
      await api.put(`/users/${userId}/toggle-active`)
      await loadUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    }
  }

  async function handlePermissionChange(userId, modulo, accao, value) {
    const user = users.find((u) => u.id === userId)
    if (!user) return

    const perm = user.permissoes.find((p) => p.modulo === modulo) || {}
    const updated = {
      modulo,
      pode_visualizar: perm.pode_visualizar || false,
      pode_criar: perm.pode_criar || false,
      pode_editar: perm.pode_editar || false,
      pode_excluir: perm.pode_excluir || false,
      [accao]: value,
    }

    if (accao === 'pode_visualizar' && !value) {
      updated.pode_criar = false
      updated.pode_editar = false
      updated.pode_excluir = false
    }
    if (accao !== 'pode_visualizar' && value) {
      updated.pode_visualizar = true
    }

    try {
      await api.put(`/users/${userId}/permissoes`, { permissoes: [updated] })
      await loadUsers()
    } catch (err) {
      alert('Erro ao salvar permissão')
    }
  }

  async function handleSelectAllRow(userId, modulo) {
    const user = users.find((u) => u.id === userId)
    const perm = user?.permissoes?.find((p) => p.modulo === modulo)
    const allChecked = perm && ACOES.every((a) => perm[a.key])

    const updated = {
      modulo,
      pode_visualizar: !allChecked,
      pode_criar: !allChecked,
      pode_editar: !allChecked,
      pode_excluir: !allChecked,
    }

    try {
      await api.put(`/users/${userId}/permissoes`, { permissoes: [updated] })
      await loadUsers()
    } catch (err) {
      alert('Erro ao salvar')
    }
  }

  async function handleSelectAllColumn(userId, accao) {
    const user = users.find((u) => u.id === userId)
    if (!user) return

    const allChecked = MODULOS.every((m) => {
      const p = user.permissoes.find((p) => p.modulo === m.key)
      return p && p[accao]
    })

    const permissoes = MODULOS.map((m) => {
      const existing = user.permissoes.find((p) => p.modulo === m.key) || {}
      const updated = {
        modulo: m.key,
        pode_visualizar: existing.pode_visualizar || false,
        pode_criar: existing.pode_criar || false,
        pode_editar: existing.pode_editar || false,
        pode_excluir: existing.pode_excluir || false,
        [accao]: !allChecked,
      }
      if (accao !== 'pode_visualizar' && !allChecked) {
        updated.pode_visualizar = true
      }
      if (accao === 'pode_visualizar' && allChecked) {
        updated.pode_criar = false
        updated.pode_editar = false
        updated.pode_excluir = false
      }
      return updated
    })

    try {
      await api.put(`/users/${userId}/permissoes`, { permissoes })
      await loadUsers()
    } catch (err) {
      alert('Erro ao salvar')
    }
  }

  async function handleResetPassword(userId) {
    if (!newPassword || newPassword.length < 6) {
      alert('A senha deve ter pelo menos 6 caracteres')
      return
    }
    try {
      await api.put(`/users/${userId}/reset-password`, { new_password: newPassword })
      setShowResetPassword(null)
      setNewPassword('')
      alert('Senha resetada com sucesso')
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    }
  }

  const funcionarios = users.filter((u) => !u.is_admin)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Funcionários</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie os acessos da equipe</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
        >
          <Plus size={18} />
          Novo Funcionário
        </button>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold">Novo Funcionário</h2>
              <button onClick={() => setShowForm(false)} className="text-dark-400 hover:text-dark-600">
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Nome completo</label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Senha</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  placeholder="Mínimo 6 caracteres"
                  minLength={6}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Telefone</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  placeholder="65 9 9999-9999"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50"
                >
                  {saving ? 'Criando...' : 'Criar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : funcionarios.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <UserCog size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum funcionário cadastrado</p>
        </div>
      ) : (
        <div className="space-y-3">
          {funcionarios.map((user) => {
            const isExpanded = expandedUser === user.id
            return (
              <div key={user.id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
                <div
                  className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-dark-50 transition"
                  onClick={() => setExpandedUser(isExpanded ? null : user.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold',
                      user.activo ? 'bg-lac-100 text-lac-700' : 'bg-dark-200 text-dark-500'
                    )}>
                      {user.full_name?.charAt(0)?.toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium text-dark-900">{user.full_name}</p>
                      <p className="text-sm text-dark-500">{user.email}</p>
                    </div>
                    {!user.activo && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">
                        Inativo
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleToggleActive(user.id) }}
                      className={cn(
                        'p-2 rounded-lg transition',
                        user.activo ? 'text-lac-600 hover:bg-lac-50' : 'text-dark-400 hover:bg-dark-100'
                      )}
                      title={user.activo ? 'Desativar' : 'Ativar'}
                    >
                      {user.activo ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setShowResetPassword(showResetPassword === user.id ? null : user.id)
                      }}
                      className="p-2 rounded-lg text-dark-400 hover:bg-dark-100 transition"
                      title="Resetar senha"
                    >
                      <KeyRound size={18} />
                    </button>
                    {isExpanded ? <ChevronUp size={18} className="text-dark-400" /> : <ChevronDown size={18} className="text-dark-400" />}
                  </div>
                </div>

                {showResetPassword === user.id && (
                  <div className="px-5 pb-4 flex items-center gap-3 border-t border-dark-100 pt-3">
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Nova senha (mín. 6 caracteres)"
                      className="flex-1 px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                      onClick={(e) => e.stopPropagation()}
                    />
                    <button
                      onClick={(e) => { e.stopPropagation(); handleResetPassword(user.id) }}
                      className="px-4 py-2 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition"
                    >
                      Resetar
                    </button>
                  </div>
                )}

                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-dark-100">
                    <div className="flex items-center gap-2 mt-4 mb-3">
                      <Shield size={16} className="text-solar-600" />
                      <h3 className="text-sm font-semibold text-dark-700">Permissões</h3>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-dark-200">
                            <th className="text-left py-2 pr-4 font-medium text-dark-600">Módulo</th>
                            {ACOES.map((a) => (
                              <th key={a.key} className="text-center py-2 px-3 font-medium text-dark-600">
                                <button
                                  onClick={() => handleSelectAllColumn(user.id, a.key)}
                                  className="hover:text-solar-600 transition"
                                >
                                  {a.label}
                                </button>
                              </th>
                            ))}
                            <th className="text-center py-2 px-2 font-medium text-dark-400 text-xs">Tudo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {MODULOS.map((m) => {
                            const perm = user.permissoes?.find((p) => p.modulo === m.key) || {}
                            return (
                              <tr key={m.key} className="border-b border-dark-100 last:border-0">
                                <td className="py-2.5 pr-4 text-dark-700">{m.label}</td>
                                {ACOES.map((a) => (
                                  <td key={a.key} className="text-center py-2.5 px-3">
                                    <input
                                      type="checkbox"
                                      checked={perm[a.key] || false}
                                      onChange={(e) => handlePermissionChange(user.id, m.key, a.key, e.target.checked)}
                                      className="w-4 h-4 rounded border-dark-300 text-solar-500 focus:ring-solar-500/50 cursor-pointer accent-solar-500"
                                    />
                                  </td>
                                ))}
                                <td className="text-center py-2.5 px-2">
                                  <button
                                    onClick={() => handleSelectAllRow(user.id, m.key)}
                                    className="text-xs text-dark-400 hover:text-solar-600 transition"
                                  >
                                    <Check size={14} />
                                  </button>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}