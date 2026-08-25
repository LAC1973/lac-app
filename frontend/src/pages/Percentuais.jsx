import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import { PieChart, Plus, X, AlertTriangle, CheckCircle } from 'lucide-react'

export default function Percentuais() {
  const { hasPermission } = useAuth()
  const [usinas, setUsinas] = useState([])
  const [usinaId, setUsinaId] = useState('')
  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(null)
  const [form, setForm] = useState({ percentual: '', data_vigencia: '' })
  const [saving, setSaving] = useState(false)

  var canEdit = hasPermission('percentuais', 'criar')

  useEffect(function () { loadUsinas() }, [])
  useEffect(function () { if (usinaId) loadPercentuais() }, [usinaId])

  async function loadUsinas() {
    try {
      var res = await api.get('/usinas/')
      setUsinas(res.data)
      if (res.data.length > 0) setUsinaId(String(res.data[0].id))
    } catch (err) {
      console.error('Erro:', err)
    }
  }

  async function loadPercentuais() {
    setLoading(true)
    try {
      var res = await api.get('/percentuais/usina/' + usinaId)
      setDados(res.data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(ucId) {
    if (!form.percentual || !form.data_vigencia) {
      alert('Preencha percentual e data de vigencia')
      return
    }
    setSaving(true)
    try {
      await api.post('/percentuais/', {
        cliente_uc_id: ucId,
        usina_id: parseInt(usinaId),
        percentual: parseFloat(form.percentual),
        data_vigencia: form.data_vigencia,
      })
      setShowAdd(null)
      setForm({ percentual: '', data_vigencia: '' })
      await loadPercentuais()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar percentual')
    } finally {
      setSaving(false)
    }
  }

  var soma = dados?.soma_percentuais || 0
  var completo = dados?.completo || false

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Percentuais</h1>
          <p className="text-dark-500 text-sm mt-1">Distribuicao de energia por UC em cada usina</p>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <select value={usinaId} onChange={function (e) { setUsinaId(e.target.value) }}
          className="px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50">
          <option value="">Selecione a usina</option>
          {usinas.map(function (u) {
            return (<option key={u.id} value={u.id}>{u.nome}</option>)
          })}
        </select>

        {dados && (
          <div className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
            completo ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
          )}>
            {completo ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
            Soma: {soma.toFixed(2)}%
            {!completo && ' (deve ser 100%)'}
          </div>
        )}
      </div>

      {!usinaId ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <PieChart size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Selecione uma usina para ver os percentuais</p>
        </div>
      ) : loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : !dados || dados.clientes.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <PieChart size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhuma UC cadastrada nesta usina</p>
          <p className="text-sm text-dark-400 mt-1">Cadastre UCs nos clientes primeiro</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-200 bg-dark-50">
                <th className="text-center py-3 px-3 font-medium text-dark-600 w-12">Item</th>
                <th className="text-left py-3 px-4 font-medium text-dark-600">Titular</th>
                <th className="text-left py-3 px-4 font-medium text-dark-600">Nome UC</th>
                <th className="text-left py-3 px-4 font-medium text-dark-600">Numero UC</th>
                <th className="text-center py-3 px-4 font-medium text-dark-600">Percentual</th>
                <th className="text-center py-3 px-4 font-medium text-dark-600">Vigencia</th>
                {canEdit && <th className="text-center py-3 px-4 font-medium text-dark-600">Acao</th>}
              </tr>
            </thead>
            <tbody>
              {dados.clientes.map(function (c) {
                var pv = c.percentual_vigente
                var isAdding = showAdd === c.uc_id
                return (
                  <tr key={c.uc_id} className="border-b border-dark-100 hover:bg-dark-50">
                    <td className="py-3 px-3 text-center text-dark-400">{c.item || '-'}</td>
                    <td className="py-3 px-4 font-medium text-dark-900">{c.nome_cliente}</td>
                    <td className="py-3 px-4 text-dark-700">{c.nome_uc || '-'}</td>
                    <td className="py-3 px-4 text-dark-600">{c.numero_uc || '-'}</td>
                    <td className="py-3 px-4 text-center">
                      {pv ? (
                        <span className="text-lg font-bold text-solar-600">{pv.percentual}%</span>
                      ) : (
                        <span className="text-dark-400">Nao definido</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center text-dark-500">
                      {pv ? new Date(pv.data_vigencia + 'T12:00:00').toLocaleDateString('pt-BR') : '-'}
                    </td>
                    {canEdit && (
                      <td className="py-3 px-4 text-center">
                        {isAdding ? (
                          <div className="flex items-center justify-center gap-2">
                            <input type="number" value={form.percentual}
                              onChange={function (e) { setForm({ ...form, percentual: e.target.value }) }}
                              placeholder="%" step="any"
                              className="w-20 px-2 py-1.5 rounded border border-dark-300 text-sm text-center focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
                            <input type="date" value={form.data_vigencia}
                              onChange={function (e) { setForm({ ...form, data_vigencia: e.target.value }) }}
                              className="px-2 py-1.5 rounded border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
                            <button onClick={function () { handleAdd(c.uc_id) }} disabled={saving}
                              className="px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-xs font-medium hover:bg-solar-600 transition disabled:opacity-50">
                              {saving ? '...' : 'Salvar'}
                            </button>
                            <button onClick={function () { setShowAdd(null); setForm({ percentual: '', data_vigencia: '' }) }}
                              className="text-dark-400 hover:text-dark-600">
                              <X size={16} />
                            </button>
                          </div>
                        ) : (
                          <button onClick={function () { setShowAdd(c.uc_id) }}
                            className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1 mx-auto">
                            <Plus size={14} /> Alterar
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr className={cn('font-semibold', completo ? 'bg-green-50' : 'bg-yellow-50')}>
                <td className="py-3 px-3"></td>
                <td className="py-3 px-4" colSpan={2}>Total</td>
                <td className="py-3 px-4"></td>
                <td className="py-3 px-4 text-center text-lg">
                  <span className={completo ? 'text-green-700' : 'text-yellow-700'}>{soma.toFixed(2)}%</span>
                </td>
                <td className="py-3 px-4" colSpan={canEdit ? 2 : 1}></td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}