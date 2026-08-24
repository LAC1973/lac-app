import { useState, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { SlidersHorizontal, Check } from 'lucide-react'

const LABELS = {
  tarifa_energisa_kwh: 'Tarifa Energisa (R$/kWh)',
}

export default function Configuracoes() {
  const { isAdmin } = useAuth()
  const [configs, setConfigs] = useState([])
  const [loading, setLoading] = useState(true)
  const [valores, setValores] = useState({})
  const [saving, setSaving] = useState(null)
  const [salvo, setSalvo] = useState(null)

  async function loadConfigs() {
    setLoading(true)
    try {
      const { data } = await api.get('/configuracoes/')
      setConfigs(data)
      setValores(Object.fromEntries(data.map((c) => [c.chave, c.valor])))
    } catch (err) {
      console.error('Erro ao carregar configurações:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(chave) {
    setSaving(chave)
    setSalvo(null)
    try {
      await api.put(`/configuracoes/${chave}`, { valor: valores[chave] })
      setSalvo(chave)
      setTimeout(() => setSalvo(null), 2000)
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(null)
    }
  }

  useEffect(() => {
    loadConfigs()
  }, [])

  if (!isAdmin()) return <Navigate to="/" replace />

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dark-900">Configurações</h1>
        <p className="text-dark-500 text-sm mt-1">Parâmetros gerais usados nos cálculos do sistema</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : configs.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <SlidersHorizontal size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhuma configuração cadastrada</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dark-200 shadow-sm divide-y divide-dark-100">
          {configs.map((c) => (
            <div key={c.chave} className="p-5">
              <label className="block text-sm font-medium text-dark-700 mb-1">
                {LABELS[c.chave] || c.chave}
              </label>
              {c.descricao && <p className="text-xs text-dark-400 mb-3">{c.descricao}</p>}
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={valores[c.chave] ?? ''}
                  onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })}
                  className="w-48 px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                />
                <button
                  onClick={() => handleSave(c.chave)}
                  disabled={saving === c.chave}
                  className="px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50"
                >
                  {saving === c.chave ? 'Salvando...' : 'Salvar'}
                </button>
                {salvo === c.chave && (
                  <span className="flex items-center gap-1 text-sm text-green-600">
                    <Check size={16} /> Salvo
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
