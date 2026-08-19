import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { Plus, Trash2, X, TrendingUp, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Despesas() {
  const { hasPermission } = useAuth()
  const [despesas, setDespesas] = useState([])
  const [financiamentos, setFinanciamentos] = useState([])
  const [loading, setLoading] = useState(true)
  const [mesRef, setMesRef] = useState(() => {
    const d = new Date()
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-01'
  })
  const [showForm, setShowForm] = useState(false)
  const [showFormFin, setShowFormFin] = useState(false)
  const [form, setForm] = useState({ categoria: '', subcategoria: '', valor_mensal: '' })
  const [formFin, setFormFin] = useState({ nome: '', valor_mensal: '' })
  const [saving, setSaving] = useState(false)

  const canCreate = hasPermission('despesas', 'criar')
  const canDelete = hasPermission('despesas', 'excluir')

  useEffect(() => { loadDados() }, [mesRef])

  async function loadDados() {
    setLoading(true)
    try {
      const [d, f] = await Promise.all([
        api.get('/despesas/?mes_referencia=' + mesRef),
        api.get('/financiamentos/?mes_referencia=' + mesRef),
      ])
      setDespesas(d.data)
      setFinanciamentos(f.data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleAddDespesa(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/despesas/', { ...form, valor_mensal: parseFloat(form.valor_mensal), mes_referencia: mesRef })
      setShowForm(false)
      setForm({ categoria: '', subcategoria: '', valor_mensal: '' })
      await loadDados()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    } finally {
      setSaving(false)
    }
  }

  async function handleAddFinanciamento(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/financiamentos/', { ...formFin, valor_mensal: parseFloat(formFin.valor_mensal), mes_referencia: mesRef })
      setShowFormFin(false)
      setFormFin({ nome: '', valor_mensal: '' })
      await loadDados()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteDespesa(id) {
    if (!confirm('Excluir esta despesa?')) return
    try {
      await api.delete('/despesas/' + id)
      await loadDados()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  async function handleDeleteFinanciamento(id) {
    if (!confirm('Excluir este financiamento?')) return
    try {
      await api.delete('/financiamentos/' + id)
      await loadDados()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  function changeMes(offset) {
    const d = new Date(mesRef + 'T12:00:00')
    d.setMonth(d.getMonth() + offset)
    setMesRef(d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-01')
  }

  const nomesMes = ['', 'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
  const mesAtual = parseInt(mesRef.split('-')[1])
  const anoAtual = parseInt(mesRef.split('-')[0])

  const totalDespesas = despesas.reduce((s, d) => s + (d.valor_mensal || 0), 0)
  const totalFinanciamentos = financiamentos.reduce((s, f) => s + (f.valor_mensal || 0), 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Despesas e Financiamentos</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie as despesas operacionais</p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 mb-6">
        <button onClick={() => changeMes(-1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronLeft size={20} /></button>
        <h2 className="text-lg font-semibold text-dark-900 w-48 text-center">{nomesMes[mesAtual]} {anoAtual}</h2>
        <button onClick={() => changeMes(1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronRight size={20} /></button>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm">
          <span className="text-sm text-red-500">Despesas Operacionais</span>
          <p className="text-xl font-bold text-red-600">{formatCurrency(totalDespesas)}</p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm">
          <span className="text-sm text-red-500">Financiamentos</span>
          <p className="text-xl font-bold text-red-600">{formatCurrency(totalFinanciamentos)}</p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border border-dark-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-dark-900">Despesas Operacionais</h2>
              {canCreate && (
                <button onClick={() => setShowForm(!showForm)} className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
                  <Plus size={14} /> Adicionar
                </button>
              )}
            </div>

            {showForm && (
              <form onSubmit={handleAddDespesa} className="mb-4 p-3 bg-dark-50 rounded-lg space-y-2">
                <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required>
                  <option value="">Categoria</option>
                  <option value="Condominio">Condominio</option>
                  <option value="Energisa">Energisa</option>
                  <option value="Pessoal">Pessoal</option>
                  <option value="Comissionamento">Comissionamento</option>
                  <option value="Outros">Outros</option>
                </select>
                <input type="text" value={form.subcategoria} onChange={(e) => setForm({ ...form, subcategoria: e.target.value })}
                  placeholder="Descricao (ex: Silvio Pascoalino)" className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
                <input type="number" value={form.valor_mensal} onChange={(e) => setForm({ ...form, valor_mensal: e.target.value })}
                  placeholder="Valor (R$)" step="any" className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required />
                <div className="flex gap-2">
                  <button type="submit" disabled={saving} className="px-4 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
                    {saving ? '...' : 'Salvar'}
                  </button>
                  <button type="button" onClick={() => setShowForm(false)} className="px-4 py-1.5 rounded-lg border border-dark-300 text-sm text-dark-600">Cancelar</button>
                </div>
              </form>
            )}

            {despesas.length === 0 ? (
              <p className="text-sm text-dark-400">Nenhuma despesa cadastrada</p>
            ) : (
              <div className="space-y-2">
                {despesas.map((d) => (
                  <div key={d.id} className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
                    <div>
                      <span className="text-sm font-medium text-dark-700">{d.categoria}</span>
                      {d.subcategoria && <span className="text-xs text-dark-400 ml-2">{d.subcategoria}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-red-600">{formatCurrency(d.valor_mensal)}</span>
                      {canDelete && (
                        <button onClick={() => handleDeleteDespesa(d.id)} className="p-1 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-dark-200 shadow-sm p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-dark-900">Financiamentos</h2>
              {canCreate && (
                <button onClick={() => setShowFormFin(!showFormFin)} className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
                  <Plus size={14} /> Adicionar
                </button>
              )}
            </div>

            {showFormFin && (
              <form onSubmit={handleAddFinanciamento} className="mb-4 p-3 bg-dark-50 rounded-lg space-y-2">
                <input type="text" value={formFin.nome} onChange={(e) => setFormFin({ ...formFin, nome: e.target.value })}
                  placeholder="Nome (ex: Creditas)" className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required />
                <input type="number" value={formFin.valor_mensal} onChange={(e) => setFormFin({ ...formFin, valor_mensal: e.target.value })}
                  placeholder="Valor (R$)" step="any" className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required />
                <div className="flex gap-2">
                  <button type="submit" disabled={saving} className="px-4 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
                    {saving ? '...' : 'Salvar'}
                  </button>
                  <button type="button" onClick={() => setShowFormFin(false)} className="px-4 py-1.5 rounded-lg border border-dark-300 text-sm text-dark-600">Cancelar</button>
                </div>
              </form>
            )}

            {financiamentos.length === 0 ? (
              <p className="text-sm text-dark-400">Nenhum financiamento cadastrado</p>
            ) : (
              <div className="space-y-2">
                {financiamentos.map((f) => (
                  <div key={f.id} className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
                    <span className="text-sm font-medium text-dark-700">{f.nome}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-red-600">{formatCurrency(f.valor_mensal)}</span>
                      {canDelete && (
                        <button onClick={() => handleDeleteFinanciamento(f.id)} className="p-1 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}