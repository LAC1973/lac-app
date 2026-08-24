import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCurrency, formatCPF, validateCPF, formatPhone } from '@/lib/utils'
import FormField from '@/components/FormField'
import DocumentosSection from '@/components/DocumentosSection'
import {
  Plus, Users, Pencil, Trash2, X, ChevronDown, ChevronUp,
  Search, PieChart,
} from 'lucide-react'

const TIPOS_DOC_CLIENTE = [
  { key: 'contrato', label: 'Contrato' },
  { key: 'cnh', label: 'CNH' },
  { key: 'comprovante_endereco', label: 'Comprovante de Endereco' },
]

export default function Clientes() {
  const { hasPermission } = useAuth()
  const [clientes, setClientes] = useState([])
  const [usinas, setUsinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingCliente, setEditingCliente] = useState(null)
  const [expandedCliente, setExpandedCliente] = useState(null)
  const [filtroUsina, setFiltroUsina] = useState('')
  const [busca, setBusca] = useState('')

  const canCreate = hasPermission('clientes', 'criar')
  const canEdit = hasPermission('clientes', 'editar')
  const canDelete = hasPermission('clientes', 'excluir')
  const canViewPercentuais = hasPermission('percentuais', 'visualizar')
  const canEditPercentuais = hasPermission('percentuais', 'criar')

  async function loadClientes() {
    setLoading(true)
    try {
      const url = filtroUsina ? `/clientes/?usina_id=${filtroUsina}` : '/clientes/'
      const { data } = await api.get(url)
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

  useEffect(() => {
    loadUsinas()
  }, [])

  useEffect(() => { loadClientes() }, [filtroUsina])

  async function handleDelete(id, nome) {
    if (!confirm(`Excluir "${nome}"? Todos os dados vinculados serão perdidos.`)) return
    try {
      await api.delete(`/clientes/${id}`)
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

  const clientesFiltrados = clientes.filter((c) =>
    c.nome.toLowerCase().includes(busca.toLowerCase()) ||
    c.numero_uc?.toLowerCase().includes(busca.toLowerCase()) ||
    c.cpf_cnpj?.toLowerCase().includes(busca.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Clientes</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie os clientes das usinas</p>
        </div>
        {canCreate && (
          <button
            onClick={handleNew}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
          >
            <Plus size={18} />
            Novo Cliente
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome, UC ou CPF..."
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
          />
        </div>
        <select
          value={filtroUsina}
          onChange={(e) => setFiltroUsina(e.target.value)}
          className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
        >
          <option value="">Todas as usinas</option>
          {usinas.map((u) => (
            <option key={u.id} value={u.id}>{u.nome}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <ClienteForm
          cliente={editingCliente}
          usinas={usinas}
          onClose={handleFormClose}
          onSaved={loadClientes}
        />
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
          {clientesFiltrados.map((cliente) => {
            const isExpanded = expandedCliente === cliente.id
            return (
              <div key={cliente.id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
                <div
                  className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-dark-50 transition"
                  onClick={() => setExpandedCliente(isExpanded ? null : cliente.id)}
                >
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
                          <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-600 font-medium">
                            Agregado
                          </span>
                        )}
                        {!cliente.activo && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">
                            Inativo
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-dark-500">
                        {cliente.usinas?.nome || 'Sem usina'}
                        {cliente.numero_uc && ` · UC ${cliente.numero_uc}`}
                        {` · ${formatCurrency(cliente.valor_kwh)}/kWh`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {canEdit && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEdit(cliente) }}
                        className="p-2 rounded-lg text-dark-400 hover:text-solar-600 hover:bg-dark-100 transition"
                      >
                        <Pencil size={18} />
                      </button>
                    )}
                    {canDelete && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(cliente.id, cliente.nome) }}
                        className="p-2 rounded-lg text-dark-400 hover:text-red-500 hover:bg-dark-100 transition"
                      >
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
                      <Info label="Endereço" value={cliente.endereco} />
                      <Info label="Nome UC" value={cliente.nome_uc} />
                      <Info label="Numero UC (antigo)" value={cliente.numero_uc} />
                      <Info label="Numero UC (novo)" value={cliente.numero_uc_novo} />
                      <Info label="Usina vinculada" value={cliente.poste} />
                      <Info label="Dia Vencimento" value={cliente.dia_vencimento ? `Dia ${cliente.dia_vencimento}` : null} />
                      <Info label="Dia Leitura" value={cliente.dia_leitura ? `Dia ${cliente.dia_leitura}` : null} />
                      <Info label="Valor kWh" value={cliente.valor_kwh ? formatCurrency(cliente.valor_kwh) : null} />
                      <Info label="Contratação" value={cliente.data_contratacao} />
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
                    <DocumentosSection entityIdField="cliente_id" entityId={cliente.id} tipos={TIPOS_DOC_CLIENTE} canEdit={canEdit} canDelete={canDelete} />
                    {/* Percentuais */}
                    {canViewPercentuais && (
                      <PercentualSection
                        clienteId={cliente.id}
                        usinaId={cliente.usina_id}
                        canEdit={canEditPercentuais}
                      />
                    )}
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
      <p className="text-sm text-dark-700 mt-0.5">{value || '—'}</p>
    </div>
  )
}

function ClienteForm({ cliente, usinas, onClose, onSaved }) {
  const isEditing = !!cliente
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    usina_id: cliente?.usina_id || '',
    nome: cliente?.nome || '',
    nome_uc: cliente?.nome_uc || '',
    numero_uc: cliente?.numero_uc || '',
    cpf_cnpj: cliente?.cpf_cnpj || '',
    identidade: cliente?.identidade || '',
    celular: cliente?.celular || '',
    email: cliente?.email || '',
    endereco: cliente?.endereco || '',
    dia_vencimento: cliente?.dia_vencimento || 5,
    valor_kwh: cliente?.valor_kwh || 0.75,
    data_contratacao: cliente?.data_contratacao || '',
    poste: cliente?.poste || '',
    dia_leitura: cliente?.dia_leitura || '',
    activo: cliente?.activo ?? true,
    eh_agregado: cliente?.eh_agregado || false,
    dados_pagamento: cliente?.dados_pagamento || '',
    pix: cliente?.pix || '',
    numero_uc_novo: cliente?.numero_uc_novo || '',
  })

  function handleChange(field, value) {
    setForm({ ...form, [field]: value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)

    const payload = { ...form }
    payload.usina_id = parseInt(payload.usina_id)
    if (payload.valor_kwh) payload.valor_kwh = parseFloat(payload.valor_kwh)
    if (payload.dia_vencimento) payload.dia_vencimento = parseInt(payload.dia_vencimento)
    if (payload.dia_leitura) payload.dia_leitura = parseInt(payload.dia_leitura)

    Object.keys(payload).forEach((key) => {
      if (payload[key] === '' || payload[key] === null) delete payload[key]
    })

    try {
      if (isEditing) {
        delete payload.usina_id
        await api.put(`/clientes/${cliente.id}`, payload)
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
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-dark-600 mb-1">Usina *</label>
              <select
                value={form.usina_id}
                onChange={(e) => handleChange('usina_id', e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                required
              >
                <option value="">Selecione a usina</option>
                {usinas.map((u) => (
                  <option key={u.id} value={u.id}>{u.nome}</option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Nome *" value={form.nome} onChange={(v) => handleChange('nome', v)} required />
            <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">CPF</label>
            <input
                type="text"
                value={form.cpf_cnpj}
                onChange={(e) => handleChange('cpf_cnpj', formatCPF(e.target.value))}
                className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                placeholder="000.000.000-00"
            />
            {form.cpf_cnpj && form.cpf_cnpj.replace(/\D/g, '').length === 11 && !validateCPF(form.cpf_cnpj) && (
                <p className="text-xs text-red-500 mt-1">CPF inválido</p>
            )}
        </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Identidade" value={form.identidade} onChange={(v) => handleChange('identidade', v)} />
            <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">Celular</label>
            <input
                type="text"
                value={form.celular}
                onChange={(e) => handleChange('celular', formatPhone(e.target.value))}
                className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                placeholder="(65) 99999-9999"
            />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Email" value={form.email} onChange={(v) => handleChange('email', v)} type="email" />
            <FormField label="Endereço" value={form.endereco} onChange={(v) => handleChange('endereco', v)} />
          </div>

          <div className="border-t border-dark-200 pt-4 mt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Dados da UC</h3>
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Nome UC" value={form.nome_uc} onChange={(v) => handleChange('nome_uc', v)} />
              <FormField label="Numero UC (antigo)" value={form.numero_uc} onChange={(v) => handleChange('numero_uc', v)} placeholder="6/2877722-5" />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <FormField label="Numero UC (novo)" value={form.numero_uc_novo} onChange={(v) => handleChange('numero_uc_novo', v)} placeholder="Novo formato Energisa" />
            </div>
                        <div className="grid grid-cols-3 gap-4 mt-4">
              <FormField label="Usina vinculada" value={form.poste} onChange={(v) => handleChange('poste', v)} placeholder="usina 0 e 1" />
              <FormField label="Dia Vencimento" value={form.dia_vencimento} onChange={(v) => handleChange('dia_vencimento', v)} type="number" />
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Dia Leitura</label>
                <select
                  value={form.dia_leitura}
                  onChange={(e) => handleChange('dia_leitura', e.target.value)}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                >
                  <option value="">Selecione</option>
                  {Array.from({ length: 30 }, (_, i) => i + 1).map((d) => (
                    <option key={d} value={d}>Dia {d}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <FormField label="Valor kWh (R$)" value={form.valor_kwh} onChange={(v) => handleChange('valor_kwh', v)} type="number" />
              <FormField label="Data Contratação" value={form.data_contratacao} onChange={(v) => handleChange('data_contratacao', v)} type="date" />
            </div>
          </div>

          <div className="border-t border-dark-200 pt-4 mt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Pagamento</h3>
            <FormField label="Dados Pagamento" value={form.dados_pagamento} onChange={(v) => handleChange('dados_pagamento', v)} placeholder="Banco ITAU, ag 1356, CC 99198-2" />
            <div className="mt-4">
              <FormField label="PIX" value={form.pix} onChange={(v) => handleChange('pix', v)} placeholder="PIX Celular: 65999211041" />
            </div>
          </div>

          <div className="border-t border-dark-200 pt-4 mt-4 flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.eh_agregado}
                onChange={(e) => handleChange('eh_agregado', e.target.checked)}
                className="w-4 h-4 rounded accent-solar-500"
              />
              <span className="text-sm text-dark-700">Agregado (não paga)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => handleChange('activo', e.target.checked)}
                className="w-4 h-4 rounded accent-solar-500"
              />
              <span className="text-sm text-dark-700">Ativo</span>
            </label>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50"
            >
              {saving ? 'Salvando...' : isEditing ? 'Salvar' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function PercentualSection({ clienteId, usinaId, canEdit }) {
  const [percentuais, setPercentuais] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ percentual: '', data_vigencia: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadPercentuais() }, [clienteId])

  async function loadPercentuais() {
    setLoading(true)
    try {
      const { data } = await api.get(`/percentuais/cliente/${clienteId}`)
      setPercentuais(data)
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
      await api.post('/percentuais/', {
        cliente_id: clienteId,
        usina_id: usinaId,
        percentual: parseFloat(form.percentual),
        data_vigencia: form.data_vigencia,
      })
      setShowAdd(false)
      setForm({ percentual: '', data_vigencia: '' })
      await loadPercentuais()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar percentual')
    } finally {
      setSaving(false)
    }
  }

  const vigente = percentuais[0]

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <PieChart size={16} className="text-solar-600" />
          <h3 className="text-sm font-semibold text-dark-700">Percentual</h3>
          {vigente && (
            <span className="text-sm font-bold text-solar-600">{vigente.percentual}%</span>
          )}
        </div>
        {canEdit && (
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1"
          >
            <Plus size={14} /> Novo percentual
          </button>
        )}
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="flex items-center gap-2 mb-3">
          <input
            type="number"
            value={form.percentual}
            onChange={(e) => setForm({ ...form, percentual: e.target.value })}
            placeholder="% (ex: 15.5)"
            className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-solar-500/50"
            step="any"
            required
          />
          <input
            type="date"
            value={form.data_vigencia}
            onChange={(e) => setForm({ ...form, data_vigencia: e.target.value })}
            className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
            required
          />
          <button type="submit" disabled={saving} className="px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
            {saving ? '...' : 'Salvar'}
          </button>
          <button type="button" onClick={() => setShowAdd(false)} className="text-dark-400 hover:text-dark-600">
            <X size={16} />
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-dark-400">Carregando...</p>
      ) : percentuais.length === 0 ? (
        <p className="text-sm text-dark-400">Nenhum percentual definido</p>
      ) : (
        <div className="space-y-1">
          {percentuais.map((p, idx) => (
            <div key={p.id} className={cn(
              'flex items-center justify-between p-2 rounded-lg text-sm',
              idx === 0 ? 'bg-solar-50 text-solar-800 font-medium' : 'bg-dark-50 text-dark-500'
            )}>
              <span>{p.percentual}%</span>
              <span className="text-xs">
                {idx === 0 ? 'Vigente desde ' : 'De '}
                {new Date(p.data_vigencia).toLocaleDateString('pt-BR')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
