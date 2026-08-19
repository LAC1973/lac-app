import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import {
  Plus, FileText, Pencil, Trash2, X, Search,
  ChevronLeft, ChevronRight, CircleDot, Download, ClipboardList, Upload,
} from 'lucide-react'

const STATUS_CONFIG = {
  pendente: { label: 'Pendente', bg: 'bg-yellow-100', text: 'text-yellow-700' },
  enviada: { label: 'Enviada', bg: 'bg-blue-100', text: 'text-blue-700' },
  paga: { label: 'Paga', bg: 'bg-green-100', text: 'text-green-700' },
  atrasada: { label: 'Atrasada', bg: 'bg-red-100', text: 'text-red-700' },
}

export default function Faturas() {
  const { hasPermission } = useAuth()
  const [faturas, setFaturas] = useState([])
  const [usinas, setUsinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [filtroUsina, setFiltroUsina] = useState('')
  const [filtroStatus, setFiltroStatus] = useState('')
  const [mesRef, setMesRef] = useState(() => {
    const d = new Date()
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-01'
  })
  const [showNovaFatura, setShowNovaFatura] = useState(false)
  const [editingFatura, setEditingFatura] = useState(null)
  const [showLeituras, setShowLeituras] = useState(false)
  const [allClientes, setAllClientes] = useState([])

  const canCreate = hasPermission('faturas', 'criar')
  const canEdit = hasPermission('faturas', 'editar')
  const canDelete = hasPermission('faturas', 'excluir')

  useEffect(() => {
    loadUsinas()
    loadClientes()
  }, [])

  useEffect(() => { loadFaturas() }, [mesRef, filtroUsina, filtroStatus])

  async function loadClientes() {
    try {
      const { data } = await api.get('/clientes/')
      setAllClientes(data)
    } catch (err) {
      console.error('Erro:', err)
    }
  }

  async function loadUsinas() {
    try {
      const { data } = await api.get('/usinas/')
      setUsinas(data)
    } catch (err) {
      console.error('Erro:', err)
    }
  }

  async function loadFaturas() {
    setLoading(true)
    try {
      var url = '/faturas/?mes_referencia=' + mesRef
      if (filtroUsina) url += '&usina_id=' + filtroUsina
      if (filtroStatus) url += '&status=' + filtroStatus
      const { data } = await api.get(url)
      setFaturas(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleStatusChange(faturaId, novoStatus) {
    try {
      await api.put('/faturas/' + faturaId + '/status?status=' + novoStatus)
      await loadFaturas()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    }
  }

  async function handleDelete(faturaId) {
    if (!confirm('Excluir esta fatura?')) return
    try {
      await api.delete('/faturas/' + faturaId)
      await loadFaturas()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
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

  const totalFaturas = faturas.reduce((sum, f) => sum + (f.valor_final || 0), 0)
  const totalPagas = faturas.filter(f => f.status === 'paga').reduce((sum, f) => sum + (f.valor_final || 0), 0)
  const totalPendentes = faturas.filter(f => f.status !== 'paga').reduce((sum, f) => sum + (f.valor_final || 0), 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Faturas</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie as faturas mensais dos clientes</p>
        </div>
        {canCreate && (
          <button
            onClick={() => setShowNovaFatura(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
          >
            <Plus size={18} />
            Nova Fatura
          </button>
        )}
      </div>

      <div className="flex items-center justify-center gap-4 mb-6">
        <button onClick={() => changeMes(-1)} className="p-2 rounded-lg hover:bg-dark-200 transition">
          <ChevronLeft size={20} />
        </button>
        <h2 className="text-lg font-semibold text-dark-900 w-48 text-center">
          {nomesMes[mesAtual]} {anoAtual}
        </h2>
        <button onClick={() => changeMes(1)} className="p-2 rounded-lg hover:bg-dark-200 transition">
          <ChevronRight size={20} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm">
          <span className="text-sm text-dark-500">Total</span>
          <p className="text-xl font-bold">{formatCurrency(totalFaturas)}</p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm">
          <span className="text-sm text-green-600">Pagas</span>
          <p className="text-xl font-bold text-green-700">{formatCurrency(totalPagas)}</p>
        </div>
        <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm">
          <span className="text-sm text-yellow-600">Pendentes</span>
          <p className="text-xl font-bold text-yellow-700">{formatCurrency(totalPendentes)}</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <select value={filtroUsina} onChange={(e) => setFiltroUsina(e.target.value)}
          className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50">
          <option value="">Todas as usinas</option>
          {usinas.map((u) => (<option key={u.id} value={u.id}>{u.nome}</option>))}
        </select>
        <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)}
          className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50">
          <option value="">Todos os status</option>
          <option value="pendente">Pendente</option>
          <option value="enviada">Enviada</option>
          <option value="paga">Paga</option>
          <option value="atrasada">Atrasada</option>
        </select>
        {filtroUsina && canEdit && (
          <button onClick={() => setShowLeituras(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-dark-800 hover:bg-dark-900 text-white text-sm font-medium transition">
            <ClipboardList size={16} /> Preencher Leituras
          </button>
        )}
        {filtroUsina && (
          <button onClick={async () => {
            try {
              const response = await api.get('/exportar/fatura-usina?usina_id=' + filtroUsina + '&ano=' + anoAtual, { responseType: 'blob' })
              const url = window.URL.createObjectURL(new Blob([response.data]))
              const link = document.createElement('a')
              link.href = url
              link.download = 'faturas_usina_' + filtroUsina + '_' + anoAtual + '.pdf'
              link.click()
              window.URL.revokeObjectURL(url)
            } catch (err) { alert('Erro ao exportar PDF') }
          }} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lac-500 hover:bg-lac-600 text-white text-sm font-medium transition">
            <Download size={16} /> Exportar PDF
          </button>
        )}
      </div>

      {showNovaFatura && (
        <NovaFaturaModal clientes={allClientes} mesRef={mesRef}
          onClose={() => setShowNovaFatura(false)} onSaved={loadFaturas} />
      )}

      {editingFatura && (
        <FaturaEditModal fatura={editingFatura}
          onClose={() => setEditingFatura(null)} onSaved={loadFaturas} />
      )}

      {showLeituras && filtroUsina && (
        <LeiturasModal usinaId={parseInt(filtroUsina)} mesRef={mesRef}
          onClose={() => setShowLeituras(false)} onSaved={loadFaturas} />
      )}

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : faturas.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <FileText size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhuma fatura neste mes</p>
          {canCreate && (<p className="text-sm text-dark-400 mt-1">Clique em "Nova Fatura" para cadastrar</p>)}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-200 bg-dark-50">
                <th className="text-left py-3 px-4 font-medium text-dark-600">Cliente</th>
                <th className="text-left py-3 px-4 font-medium text-dark-600">Usina</th>
                <th className="text-right py-3 px-4 font-medium text-dark-600">kWh Injetado</th>
                <th className="text-right py-3 px-4 font-medium text-dark-600">Valor kWh</th>
                <th className="text-right py-3 px-4 font-medium text-dark-600">Valor Final</th>
                <th className="text-center py-3 px-4 font-medium text-dark-600">Vencimento</th>
                <th className="text-center py-3 px-4 font-medium text-dark-600">Status</th>
                <th className="text-center py-3 px-4 font-medium text-dark-600">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {faturas.map((fatura) => {
                const st = STATUS_CONFIG[fatura.status] || STATUS_CONFIG.pendente
                const clienteNome = fatura.clientes?.nome || '-'
                const usinaNome = fatura.clientes?.usinas?.nome || '-'
                return (
                  <tr key={fatura.id} className="border-b border-dark-100 hover:bg-dark-50">
                    <td className="py-3 px-4 font-medium text-dark-900">{clienteNome}</td>
                    <td className="py-3 px-4 text-dark-600">{usinaNome}</td>
                    <td className="py-3 px-4 text-right text-dark-700">{fatura.kwh_injetado?.toFixed(1) || '-'}</td>
                    <td className="py-3 px-4 text-right text-dark-700">{formatCurrency(fatura.valor_kwh_aplicado)}</td>
                    <td className="py-3 px-4 text-right font-semibold text-dark-900">{formatCurrency(fatura.valor_final)}</td>
                    <td className="py-3 px-4 text-center text-dark-600">
                      {fatura.data_vencimento ? new Date(fatura.data_vencimento + 'T12:00:00').toLocaleDateString('pt-BR') : '-'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {canEdit ? (
                        <select value={fatura.status} onChange={(e) => handleStatusChange(fatura.id, e.target.value)}
                          className={cn('text-xs font-medium px-2 py-1 rounded-full border-0 cursor-pointer', st.bg, st.text)}>
                          <option value="pendente">Pendente</option>
                          <option value="enviada">Enviada</option>
                          <option value="paga">Paga</option>
                          <option value="atrasada">Atrasada</option>
                        </select>
                      ) : (
                        <span className={cn('text-xs font-medium px-2 py-1 rounded-full', st.bg, st.text)}>{st.label}</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {canEdit && (<button onClick={() => setEditingFatura(fatura)} className="p-1.5 rounded text-dark-400 hover:text-solar-600 transition"><Pencil size={15} /></button>)}
                        {canDelete && (<button onClick={() => handleDelete(fatura.id)} className="p-1.5 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={15} /></button>)}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FaturaEditModal({ fatura, onClose, onSaved }) {
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    leitura_inicial: fatura.leitura_inicial || '',
    leitura_final: fatura.leitura_final || '',
    consumo_kwh: fatura.consumo_kwh || '',
    kwh_injetado: fatura.kwh_injetado || '',
    valor_kwh_aplicado: fatura.valor_kwh_aplicado || '',
    valor_total: fatura.valor_total || '',
    desconto_sazonal: fatura.desconto_sazonal || 0,
    valor_final: fatura.valor_final || '',
    data_vencimento: fatura.data_vencimento || '',
  })

  function handleChange(field, value) {
    const updated = { ...form, [field]: value }
    if (field === 'leitura_inicial' || field === 'leitura_final') {
      const ini = parseFloat(field === 'leitura_inicial' ? value : updated.leitura_inicial) || 0
      const fin = parseFloat(field === 'leitura_final' ? value : updated.leitura_final) || 0
      if (ini && fin) updated.consumo_kwh = (fin - ini).toFixed(1)
    }
    if (field === 'kwh_injetado' || field === 'valor_kwh_aplicado') {
      const kwh = parseFloat(field === 'kwh_injetado' ? value : updated.kwh_injetado) || 0
      const vkwh = parseFloat(field === 'valor_kwh_aplicado' ? value : updated.valor_kwh_aplicado) || 0
      updated.valor_total = (kwh * vkwh).toFixed(2)
      updated.valor_final = (kwh * vkwh - (parseFloat(updated.desconto_sazonal) || 0)).toFixed(2)
    }
    if (field === 'desconto_sazonal') {
      const vt = parseFloat(updated.valor_total) || 0
      updated.valor_final = (vt - (parseFloat(value) || 0)).toFixed(2)
    }
    setForm(updated)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    const payload = {}
    Object.entries(form).forEach(([key, value]) => {
      if (value !== '' && value !== null) {
        payload[key] = key === 'data_vencimento' ? value : parseFloat(value)
      }
    })
    try {
      await api.put('/faturas/' + fatura.id, payload)
      onClose()
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold">Editar Fatura</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600"><X size={20} /></button>
        </div>
        <p className="text-sm text-dark-500 mb-4">{fatura.clientes?.nome} - {fatura.clientes?.usinas?.nome}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <Field label="Leitura Inicial" value={form.leitura_inicial} onChange={(v) => handleChange('leitura_inicial', v)} type="number" />
            <Field label="Leitura Final" value={form.leitura_final} onChange={(v) => handleChange('leitura_final', v)} type="number" />
            <Field label="Consumo kWh" value={form.consumo_kwh} onChange={(v) => handleChange('consumo_kwh', v)} type="number" disabled />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="kWh Injetado" value={form.kwh_injetado} onChange={(v) => handleChange('kwh_injetado', v)} type="number" />
            <Field label="Valor kWh (R$)" value={form.valor_kwh_aplicado} onChange={(v) => handleChange('valor_kwh_aplicado', v)} type="number" />
            <Field label="Valor Total" value={form.valor_total} onChange={(v) => handleChange('valor_total', v)} type="number" disabled />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Desconto Sazonal" value={form.desconto_sazonal} onChange={(v) => handleChange('desconto_sazonal', v)} type="number" />
            <Field label="Valor Final" value={form.valor_final} onChange={(v) => handleChange('valor_final', v)} type="number" disabled />
            <Field label="Vencimento" value={form.data_vencimento} onChange={(v) => handleChange('data_vencimento', v)} type="date" />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition">Cancelar</button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function Field({ label, value, onChange, type = 'text', disabled }) {
  return (
    <div>
      <label className="block text-xs font-medium text-dark-500 mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}
        step={type === 'number' ? 'any' : undefined}
        className={cn('w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50',
          disabled && 'bg-dark-100 text-dark-500 cursor-not-allowed')} />
    </div>
  )
}

function LeiturasModal({ usinaId, mesRef, onClose, onSaved }) {
  const [dados, setDados] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [valores, setValores] = useState({})

  useEffect(() => { loadLeituras() }, [])

  async function loadLeituras() {
    setLoading(true)
    try {
      const { data } = await api.get('/leituras/?usina_id=' + usinaId + '&mes_referencia=' + mesRef)
      setDados(data)
      const vals = {}
      data.forEach((d) => {
        vals[d.cliente_id] = {
          leitura_inicial: d.leitura_inicial ?? d.leitura_anterior ?? '',
          leitura_final: d.leitura_final ?? '',
        }
      })
      setValores(vals)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  function handleChange(clienteId, campo, value) {
    setValores((prev) => ({ ...prev, [clienteId]: { ...prev[clienteId], [campo]: value } }))
  }

  function getConsumo(clienteId) {
    const v = valores[clienteId]
    if (!v) return ''
    const ini = parseFloat(v.leitura_inicial)
    const fin = parseFloat(v.leitura_final)
    if (isNaN(ini) || isNaN(fin)) return ''
    return (fin - ini).toFixed(0)
  }

  async function handleSave() {
    setSaving(true)
    try {
      const registros = dados.filter((d) => d.fatura_id).map((d) => ({
        fatura_id: d.fatura_id,
        leitura_inicial: valores[d.cliente_id]?.leitura_inicial ? parseFloat(valores[d.cliente_id].leitura_inicial) : null,
        leitura_final: valores[d.cliente_id]?.leitura_final ? parseFloat(valores[d.cliente_id].leitura_final) : null,
      }))
      await api.post('/leituras/', { registros })
      alert('Leituras salvas com sucesso!')
      onClose()
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const nomesMes = ['', 'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
  const mesNum = parseInt(mesRef.split('-')[1])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold">Preencher Leituras</h2>
            <p className="text-sm text-dark-500">{nomesMes[mesNum]} {mesRef.split('-')[0]}</p>
          </div>
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600"><X size={20} /></button>
        </div>
        {loading ? (
          <div className="text-center py-8 text-dark-400">Carregando...</div>
        ) : dados.length === 0 ? (
          <div className="text-center py-8 text-dark-400">Cadastre as faturas primeiro</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-200 bg-dark-50">
                    <th className="text-left py-2 px-3 font-medium text-dark-600">Cliente</th>
                    <th className="text-left py-2 px-3 font-medium text-dark-600">UC</th>
                    <th className="text-center py-2 px-3 font-medium text-dark-600">Anterior</th>
                    <th className="text-center py-2 px-3 font-medium text-dark-600">Inicial</th>
                    <th className="text-center py-2 px-3 font-medium text-dark-600">Final</th>
                    <th className="text-center py-2 px-3 font-medium text-dark-600">Consumo</th>
                    <th className="text-center py-2 px-3 font-medium text-dark-600">Injetado</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.map((d) => {
                    const v = valores[d.cliente_id] || {}
                    const consumo = getConsumo(d.cliente_id)
                    return (
                      <tr key={d.cliente_id} className="border-b border-dark-100">
                        <td className="py-2 px-3 text-dark-900 font-medium">{d.nome_uc || d.nome}</td>
                        <td className="py-2 px-3 text-dark-600 text-xs">{d.numero_uc || ''}</td>
                        <td className="py-2 px-3 text-center text-dark-400 text-xs">
                          {d.leitura_anterior != null ? d.leitura_anterior.toFixed(0) : '-'}
                        </td>
                        <td className="py-2 px-3">
                          <input type="number" value={v.leitura_inicial ?? ''} onChange={(e) => handleChange(d.cliente_id, 'leitura_inicial', e.target.value)}
                            className="w-24 px-2 py-1.5 rounded border border-dark-300 text-sm text-right focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
                        </td>
                        <td className="py-2 px-3">
                          <input type="number" value={v.leitura_final ?? ''} onChange={(e) => handleChange(d.cliente_id, 'leitura_final', e.target.value)}
                            className="w-24 px-2 py-1.5 rounded border border-dark-300 text-sm text-right focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
                        </td>
                        <td className="py-2 px-3 text-center font-medium text-dark-700">{consumo}</td>
                        <td className="py-2 px-3 text-center text-solar-600 font-medium">
                          {d.kwh_injetado != null ? d.kwh_injetado.toFixed(1) : '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex justify-end mt-4 gap-3">
              <button onClick={onClose} className="px-6 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition">Cancelar</button>
              <button onClick={handleSave} disabled={saving}
                className="px-6 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50">
                {saving ? 'Salvando...' : 'Salvar Leituras'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function NovaFaturaModal({ clientes, mesRef, onClose, onSaved }) {
  const [saving, setSaving] = useState(false)
    const [uploading, setUploading] = useState(false)

  async function handleUploadEnergisa(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post('/energisa/extrair', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setForm((prev) => ({
        ...prev,
        leitura_final: data.leitura_atual || prev.leitura_final,
        kwh_injetado: data.energia_injetada || prev.kwh_injetado,
        saldo_kwh: data.saldo_acumulado || prev.saldo_kwh,
      }))
      alert('Dados extraidos: Leitura ' + (data.leitura_atual || '-') + ', Consumo ' + (data.consumo_kwh || '-') + ', Injetada ' + (data.energia_injetada || '-') + ', Saldo ' + (data.saldo_acumulado || '-'))
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao extrair dados do PDF')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }
  const [form, setForm] = useState({
    cliente_id: '',
    mes_referencia: mesRef,
    leitura_inicial: '',
    leitura_final: '',
    kwh_injetado: '',
    saldo_kwh: '',
    desconto_sazonal: 0,
  })

  const clienteSelecionado = clientes.find((c) => c.id === parseInt(form.cliente_id))
  const valorKwh = clienteSelecionado?.valor_kwh || 0.75

  const consumo = (form.leitura_inicial && form.leitura_final)
    ? (parseFloat(form.leitura_final) - parseFloat(form.leitura_inicial)).toFixed(0) : ''

  const valorTotal = form.kwh_injetado
    ? (parseFloat(form.kwh_injetado) * valorKwh).toFixed(2) : ''

  const valorFinal = valorTotal
    ? (parseFloat(valorTotal) - (parseFloat(form.desconto_sazonal) || 0)).toFixed(2) : ''

  function handleChange(field, value) {
    setForm({ ...form, [field]: value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.kwh_injetado) { alert('kWh Injetado e obrigatorio'); return }
    if (!form.saldo_kwh && form.saldo_kwh !== 0) { alert('Saldo Acumulado e obrigatorio'); return }

    setSaving(true)
    const diaVenc = clienteSelecionado?.dia_vencimento || 5
    const ano = form.mes_referencia.split('-')[0]
    const mes = form.mes_referencia.split('-')[1]
    const dataVencimento = ano + '-' + mes + '-' + String(diaVenc).padStart(2, '0')

    const payload = {
      cliente_id: parseInt(form.cliente_id),
      mes_referencia: form.mes_referencia,
      leitura_inicial: form.leitura_inicial ? parseFloat(form.leitura_inicial) : null,
      leitura_final: form.leitura_final ? parseFloat(form.leitura_final) : null,
      consumo_kwh: consumo ? parseFloat(consumo) : null,
      kwh_injetado: parseFloat(form.kwh_injetado),
      saldo_kwh: parseFloat(form.saldo_kwh),
      valor_kwh_aplicado: valorKwh,
      valor_total: valorTotal ? parseFloat(valorTotal) : null,
      desconto_sazonal: parseFloat(form.desconto_sazonal) || 0,
      valor_final: valorFinal ? parseFloat(valorFinal) : null,
      data_vencimento: dataVencimento,
    }

    try {
      await api.post('/faturas/', payload)
      onClose()
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao cadastrar fatura')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold">Nova Fatura</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">Cliente *</label>
            <select value={form.cliente_id} onChange={(e) => handleChange('cliente_id', e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required>
              <option value="">Selecione o cliente</option>
              {clientes.filter((c) => c.activo).map((c) => (
                <option key={c.id} value={c.id}>{c.nome} - {c.usinas?.nome || ''} ({formatCurrency(c.valor_kwh)}/kWh)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">Mes Referencia *</label>
            <input type="month" value={form.mes_referencia.substring(0, 7)}
              onChange={(e) => handleChange('mes_referencia', e.target.value + '-01')}
              className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required />
          </div>
                    <div className="border-t border-dark-200 pt-4">
            <label className="flex items-center gap-2 px-4 py-3 rounded-lg bg-lac-100 hover:bg-lac-200 text-lac-800 text-sm font-medium cursor-pointer transition w-full justify-center">
              <Upload size={18} />
              {uploading ? 'Extraindo dados...' : 'Importar PDF da Energisa'}
              <input type="file" className="hidden" onChange={handleUploadEnergisa} disabled={uploading} accept=".pdf" />
            </label>
            <p className="text-xs text-dark-400 text-center mt-2">Preenche automaticamente leitura, injetado e saldo</p>
          </div>
          <div className="border-t border-dark-200 pt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Dados da Leitura</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Leitura Inicial</label>
                <input type="number" value={form.leitura_inicial} onChange={(e) => handleChange('leitura_inicial', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Leitura Final</label>
                <input type="number" value={form.leitura_final} onChange={(e) => handleChange('leitura_final', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Consumo</label>
                <input type="text" value={consumo} disabled
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm bg-dark-100 text-dark-500 cursor-not-allowed" />
              </div>
            </div>
          </div>
          <div className="border-t border-dark-200 pt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Energia e Valores</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">kWh Injetado *</label>
                <input type="number" value={form.kwh_injetado} onChange={(e) => handleChange('kwh_injetado', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Saldo Acumulado *</label>
                <input type="number" value={form.saldo_kwh} onChange={(e) => handleChange('saldo_kwh', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" required />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Valor kWh</label>
                <input type="text" value={formatCurrency(valorKwh)} disabled
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm bg-dark-100 text-dark-500 cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Desconto Sazonal</label>
                <input type="number" value={form.desconto_sazonal} onChange={(e) => handleChange('desconto_sazonal', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-500 mb-1">Valor Final</label>
                <input type="text" value={valorFinal ? formatCurrency(parseFloat(valorFinal)) : ''} disabled
                  className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm bg-dark-100 text-dark-500 cursor-not-allowed font-semibold" />
              </div>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition">Cancelar</button>
            <button type="submit" disabled={saving}
              className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50">
              {saving ? 'Salvando...' : 'Cadastrar Fatura'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
