import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCurrency, formatCPF, validateCPF, formatPhone } from '@/lib/utils'
import {
  Plus, Users, Pencil, Trash2, X, ChevronDown, ChevronUp,
  Search, Upload, Eye, Zap,
} from 'lucide-react'

export default function Clientes() {
  const { hasPermission } = useAuth()
  const [clientes, setClientes] = useState([])
  const [usinas, setUsinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingCliente, setEditingCliente] = useState(null)
  const [expandedCliente, setExpandedCliente] = useState(null)
  const [busca, setBusca] = useState('')

  const canCreate = hasPermission('clientes', 'criar')
  const canEdit = hasPermission('clientes', 'editar')
  const canDelete = hasPermission('clientes', 'excluir')

  useEffect(() => {
    loadClientes()
    loadUsinas()
  }, [])

  async function loadClientes() {
    setLoading(true)
    try {
      const { data } = await api.get('/clientes/')
      setClientes(data)
    } catch (err) {
      console.error('Erro ao carregar clientes:', err)
    } finally {
      setLoading(false)
    }
  }

  async function loadUsinas() {
    try {
      const { data } = await api.get('/usinas/')
      setUsinas(data)
    } catch (err) {
      console.error('Erro ao carregar usinas:', err)
    }
  }

  async function handleDelete(id, nome) {
    if (!confirm('Excluir "' + nome + '"? Todos os dados vinculados serao perdidos.')) return
    try {
      await api.delete('/clientes/' + id)
      await loadClientes()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  function handleEdit(cliente) {
    setEditingCliente(cliente)
    setShowForm(true)
  }

  function handleNew() {
    setEditingCliente(null)
    setShowForm(true)
  }

  function handleFormClose() {
    setShowForm(false)
    setEditingCliente(null)
  }

  var clientesFiltrados = clientes.filter(function (c) {
    var termo = busca.toLowerCase()
    return c.nome.toLowerCase().includes(termo) ||
      (c.cpf_cnpj || '').toLowerCase().includes(termo) ||
      (c.clientes_ucs || []).some(function (uc) {
        return (uc.numero_uc || '').toLowerCase().includes(termo) ||
          (uc.nome_uc || '').toLowerCase().includes(termo)
      })
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Clientes</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie os clientes e suas UCs</p>
        </div>
        {canCreate && (
          <button onClick={handleNew}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition">
            <Plus size={18} /> Novo Cliente
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
          <input type="text" value={busca} onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, UC ou CPF..."
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
        </div>
      </div>

      {showForm && (
        <ClienteForm cliente={editingCliente} onClose={handleFormClose} onSaved={loadClientes} />
      )}

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : clientesFiltrados.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <Users size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum cliente encontrado</p>
        </div>
      ) : (
        <div className="space-y-3">
          {clientesFiltrados.map(function (cliente) {
            var isExpanded = expandedCliente === cliente.id
            var totalUCs = (cliente.clientes_ucs || []).length
            return (
              <div key={cliente.id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
                <div className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-dark-50 transition"
                  onClick={function () { setExpandedCliente(isExpanded ? null : cliente.id) }}>
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      'w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold',
                      cliente.activo ? 'bg-lac-100 text-lac-700' : 'bg-dark-200 text-dark-500'
                    )}>
                      {cliente.nome?.charAt(0)?.toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-dark-900">{cliente.nome}</p>
                        {cliente.eh_agregado && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-600 font-medium">Agregado</span>
                        )}
                        {!cliente.activo && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">Inativo</span>
                        )}
                      </div>
                      <p className="text-sm text-dark-500">
                        {totalUCs + ' UC(s)'}
                        {' - ' + formatCurrency(cliente.valor_kwh) + '/kWh'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {canEdit && (
                      <button onClick={function (e) { e.stopPropagation(); handleEdit(cliente) }}
                        className="p-2 rounded-lg text-dark-400 hover:text-solar-600 hover:bg-dark-100 transition">
                        <Pencil size={18} />
                      </button>
                    )}
                    {canDelete && (
                      <button onClick={function (e) { e.stopPropagation(); handleDelete(cliente.id, cliente.nome) }}
                        className="p-2 rounded-lg text-dark-400 hover:text-red-500 hover:bg-dark-100 transition">
                        <Trash2 size={18} />
                      </button>
                    )}
                    {isExpanded ? <ChevronUp size={18} className="text-dark-400" /> : <ChevronDown size={18} className="text-dark-400" />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-dark-100">
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
                      <Info label="CPF/CNPJ" value={cliente.cpf_cnpj} />
                      <Info label="Identidade" value={cliente.identidade} />
                      <Info label="Celular" value={cliente.celular} />
                      <Info label="Email" value={cliente.email} />
                      <Info label="Endereco" value={cliente.endereco} />
                      <Info label="Dia Vencimento" value={cliente.dia_vencimento ? 'Dia ' + cliente.dia_vencimento : null} />
                      <Info label="Valor kWh" value={cliente.valor_kwh ? formatCurrency(cliente.valor_kwh) : null} />
                      <Info label="Contratacao" value={cliente.data_contratacao} />
                    </div>
                    {cliente.dados_pagamento && (
                      <div className="mt-3">
                        <span className="text-xs text-dark-400">Dados Pagamento</span>
                        <p className="text-sm text-dark-700 mt-0.5">{cliente.dados_pagamento}</p>
                      </div>
                    )}
                    {cliente.pix && (
                      <div className="mt-2">
                        <span className="text-xs text-dark-400">PIX</span>
                        <p className="text-sm text-dark-700 mt-0.5">{cliente.pix}</p>
                      </div>
                    )}

                    <UCsSection clienteId={cliente.id} usinas={usinas} canEdit={canEdit} canDelete={canDelete} onSaved={loadClientes} />

                    <ClienteDocumentosSection clienteId={cliente.id} canEdit={canEdit} canDelete={canDelete} />
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

function Info({ label, value }) {
  return (
    <div>
      <span className="text-xs text-dark-400">{label}</span>
      <p className="text-sm text-dark-700 mt-0.5">{value || '-'}</p>
    </div>
  )
}

function ClienteForm({ cliente, onClose, onSaved }) {
  var isEditing = !!cliente
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    nome: cliente?.nome || '',
    cpf_cnpj: cliente?.cpf_cnpj || '',
    identidade: cliente?.identidade || '',
    celular: cliente?.celular || '',
    email: cliente?.email || '',
    endereco: cliente?.endereco || '',
    dia_vencimento: cliente?.dia_vencimento || 5,
    valor_kwh: cliente?.valor_kwh || 0.75,
    data_contratacao: cliente?.data_contratacao || '',
    activo: cliente?.activo ?? true,
    eh_agregado: cliente?.eh_agregado || false,
    dados_pagamento: cliente?.dados_pagamento || '',
    pix: cliente?.pix || '',
  })

  function handleChange(field, value) {
    setForm({ ...form, [field]: value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)

    var payload = { ...form }
    if (payload.valor_kwh) payload.valor_kwh = parseFloat(payload.valor_kwh)
    if (payload.dia_vencimento) payload.dia_vencimento = parseInt(payload.dia_vencimento)

    Object.keys(payload).forEach(function (key) {
      if (payload[key] === '' || payload[key] === null) delete payload[key]
    })

    try {
      if (isEditing) {
        await api.put('/clientes/' + cliente.id, payload)
      } else {
        await api.post('/clientes/', payload)
      }
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
      <div className="bg-white rounded-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold">{isEditing ? 'Editar Cliente' : 'Novo Cliente'}</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Nome *" value={form.nome} onChange={function (v) { handleChange('nome', v) }} required />
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">CPF/CNPJ</label>
              <input type="text" value={form.cpf_cnpj}
                onChange={function (e) { handleChange('cpf_cnpj', formatCPF(e.target.value)) }}
                className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                placeholder="000.000.000-00" />
              {form.cpf_cnpj && form.cpf_cnpj.replace(/\D/g, '').length === 11 && !validateCPF(form.cpf_cnpj) && (
                <p className="text-xs text-red-500 mt-1">CPF invalido</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Identidade" value={form.identidade} onChange={function (v) { handleChange('identidade', v) }} />
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">Celular</label>
              <input type="text" value={form.celular}
                onChange={function (e) { handleChange('celular', formatPhone(e.target.value)) }}
                className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                placeholder="(65) 99999-9999" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Email" value={form.email} onChange={function (v) { handleChange('email', v) }} type="email" />
            <FormField label="Endereco" value={form.endereco} onChange={function (v) { handleChange('endereco', v) }} />
          </div>

          <div className="border-t border-dark-200 pt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Contrato e Pagamento</h3>
            <div className="grid grid-cols-3 gap-4">
              <FormField label="Dia Vencimento" value={form.dia_vencimento} onChange={function (v) { handleChange('dia_vencimento', v) }} type="number" />
              <FormField label="Valor kWh (R$)" value={form.valor_kwh} onChange={function (v) { handleChange('valor_kwh', v) }} type="number" />
              <FormField label="Data Contratacao" value={form.data_contratacao} onChange={function (v) { handleChange('data_contratacao', v) }} type="date" />
            </div>
            <div className="mt-4">
              <FormField label="Dados Pagamento" value={form.dados_pagamento} onChange={function (v) { handleChange('dados_pagamento', v) }} placeholder="Banco ITAU, ag 1356, CC 99198-2" />
            </div>
            <div className="mt-4">
              <FormField label="PIX" value={form.pix} onChange={function (v) { handleChange('pix', v) }} placeholder="PIX Celular: 65999211041" />
            </div>
          </div>

          <div className="border-t border-dark-200 pt-4 flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.eh_agregado}
                onChange={function (e) { handleChange('eh_agregado', e.target.checked) }}
                className="w-4 h-4 rounded accent-solar-500" />
              <span className="text-sm text-dark-700">Agregado (nao paga)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.activo}
                onChange={function (e) { handleChange('activo', e.target.checked) }}
                className="w-4 h-4 rounded accent-solar-500" />
              <span className="text-sm text-dark-700">Ativo</span>
            </label>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition">Cancelar</button>
            <button type="submit" disabled={saving} className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50">
              {saving ? 'Salvando...' : isEditing ? 'Salvar' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function FormField({ label, value, onChange, type, placeholder, required }) {
  return (
    <div>
      <label className="block text-sm font-medium text-dark-600 mb-1">{label}</label>
      <input type={type || 'text'} value={value} onChange={function (e) { onChange(e.target.value) }}
        className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
        placeholder={placeholder} required={required} step={type === 'number' ? 'any' : undefined} />
    </div>
  )
}

function UCsSection({ clienteId, usinas, canEdit, canDelete, onSaved }) {
  const [ucs, setUcs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ usina_id: '', nome_uc: '', numero_uc: '', numero_uc_novo: '', poste: '', dia_leitura: '', item: '' })

  useEffect(function () { loadUCs() }, [clienteId])

  async function loadUCs() {
    setLoading(true)
    try {
      const { data } = await api.get('/clientes/' + clienteId + '/ucs')
      setUcs(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleAdd(e) {
    e.preventDefault()
    setSaving(true)
    try {
      var payload = { ...form }
      payload.usina_id = parseInt(payload.usina_id)
      if (payload.item) payload.item = parseInt(payload.item)
      if (payload.dia_leitura) payload.dia_leitura = parseInt(payload.dia_leitura)
      Object.keys(payload).forEach(function (k) { if (payload[k] === '') delete payload[k] })
      await api.post('/clientes/' + clienteId + '/ucs', payload)
      setShowAdd(false)
      setForm({ usina_id: '', nome_uc: '', numero_uc: '', numero_uc_novo: '', poste: '', dia_leitura: '', item: '' })
      await loadUCs()
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao adicionar UC')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteUC(ucId) {
    if (!confirm('Excluir esta UC?')) return
    try {
      await api.delete('/clientes/ucs/' + ucId)
      await loadUCs()
      await onSaved()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-solar-600" />
          <h3 className="text-sm font-semibold text-dark-700">Unidades Consumidoras (UCs)</h3>
        </div>
        {canEdit && (
          <button onClick={function () { setShowAdd(!showAdd) }}
            className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
            <Plus size={14} /> Adicionar UC
          </button>
        )}
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="mb-3 p-3 bg-dark-50 rounded-lg space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <select value={form.usina_id} onChange={function (e) { setForm({ ...form, usina_id: e.target.value }) }}
              className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" required>
              <option value="">Usina *</option>
              {usinas.map(function (u) { return (<option key={u.id} value={u.id}>{u.nome}</option>) })}
            </select>
            <input type="text" value={form.nome_uc} onChange={function (e) { setForm({ ...form, nome_uc: e.target.value }) }}
              placeholder="Nome da UC" className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input type="text" value={form.numero_uc} onChange={function (e) { setForm({ ...form, numero_uc: e.target.value }) }}
              placeholder="Numero UC (antigo)" className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
            <input type="text" value={form.numero_uc_novo} onChange={function (e) { setForm({ ...form, numero_uc_novo: e.target.value }) }}
              placeholder="Numero UC (novo)" className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
            <input type="text" value={form.poste} onChange={function (e) { setForm({ ...form, poste: e.target.value }) }}
              placeholder="Poste" className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <select value={form.dia_leitura} onChange={function (e) { setForm({ ...form, dia_leitura: e.target.value }) }}
              className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50">
              <option value="">Dia Leitura</option>
              {Array.from({ length: 30 }, function (_, i) { return i + 1 }).map(function (d) {
                return (<option key={d} value={d}>Dia {d}</option>)
              })}
            </select>
            <input type="number" value={form.item} onChange={function (e) { setForm({ ...form, item: e.target.value }) }}
              placeholder="Item (num. sequencial)" className="px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving}
              className="px-4 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
              {saving ? '...' : 'Salvar UC'}
            </button>
            <button type="button" onClick={function () { setShowAdd(false) }}
              className="px-4 py-1.5 rounded-lg border border-dark-300 text-sm text-dark-600">Cancelar</button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-dark-400">Carregando...</p>
      ) : ucs.length === 0 ? (
        <p className="text-sm text-dark-400">Nenhuma UC cadastrada</p>
      ) : (
        <div className="space-y-2">
          {ucs.map(function (uc) {
            return (
              <div key={uc.id} className="flex items-center justify-between p-3 bg-dark-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Zap size={14} className="text-solar-500" />
                    <span className="text-sm font-medium text-dark-900">{uc.nome_uc || 'UC sem nome'}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-solar-100 text-solar-700">{uc.usinas?.nome || ''}</span>
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-xs text-dark-500">UC: {uc.numero_uc || '-'}</span>
                    {uc.numero_uc_novo && <span className="text-xs text-dark-500">Novo: {uc.numero_uc_novo}</span>}
                    {uc.poste && <span className="text-xs text-dark-500">Poste: {uc.poste}</span>}
                    {uc.dia_leitura && <span className="text-xs text-dark-500">Leitura: Dia {uc.dia_leitura}</span>}
                    {uc.item && <span className="text-xs text-dark-400">Item {uc.item}</span>}
                  </div>
                </div>
                {canDelete && (
                  <button onClick={function () { handleDeleteUC(uc.id) }}
                    className="p-1.5 rounded text-dark-400 hover:text-red-500 transition">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ClienteDocumentosSection({ clienteId, canEdit, canDelete }) {
  var TIPOS_DOC = [
    { key: 'contrato', label: 'Contrato' },
    { key: 'cnh', label: 'CNH' },
    { key: 'comprovante_endereco', label: 'Comprovante de Endereco' },
  ]

  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [tipoUpload, setTipoUpload] = useState('')

  useEffect(function () { loadDocs() }, [clienteId])

  async function loadDocs() {
    setLoading(true)
    try {
      const { data } = await api.get('/documentos/?cliente_id=' + clienteId)
      setDocs(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    var file = e.target.files[0]
    if (!file || !tipoUpload) return
    setUploading(true)
    try {
      var formData = new FormData()
      formData.append('file', file)
      formData.append('tipo', tipoUpload)
      formData.append('cliente_id', clienteId)
      await api.post('/documentos/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setTipoUpload('')
      await loadDocs()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro no upload')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleDelete(docId) {
    if (!confirm('Excluir este documento?')) return
    try {
      await api.delete('/documentos/' + docId)
      await loadDocs()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  var tipoLabel = function (tipo) {
    var found = TIPOS_DOC.find(function (t) { return t.key === tipo })
    return found ? found.label : tipo
  }

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-dark-700">Documentos</h3>
        {canEdit && (
          <div className="flex items-center gap-2">
            <select value={tipoUpload} onChange={function (e) { setTipoUpload(e.target.value) }}
              className="px-2 py-1.5 rounded-lg border border-dark-300 text-xs focus:outline-none focus:ring-2 focus:ring-solar-500/50">
              <option value="">Tipo</option>
              {TIPOS_DOC.map(function (t) { return (<option key={t.key} value={t.key}>{t.label}</option>) })}
            </select>
            <label className={cn(
              'flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition',
              tipoUpload ? 'bg-solar-500 text-dark-900 hover:bg-solar-600' : 'bg-dark-200 text-dark-400 cursor-not-allowed'
            )}>
              Upload
              <input type="file" className="hidden" onChange={handleUpload} disabled={!tipoUpload || uploading} accept=".pdf,.jpg,.jpeg,.png" />
            </label>
          </div>
        )}
      </div>
      {loading ? (
        <p className="text-sm text-dark-400">Carregando...</p>
      ) : docs.length === 0 ? (
        <p className="text-sm text-dark-400">Nenhum documento enviado</p>
      ) : (
        <div className="space-y-2">
          {docs.map(function (doc) {
            return (
              <div key={doc.id} className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-dark-700">{doc.nome_arquivo}</span>
                  <span className="text-xs text-dark-400">{tipoLabel(doc.tipo)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="text-xs text-solar-600 hover:text-solar-700">Ver</a>
                  {canDelete && (
                    <button onClick={function () { handleDelete(doc.id) }} className="text-xs text-red-400 hover:text-red-600 ml-2">Excluir</button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
