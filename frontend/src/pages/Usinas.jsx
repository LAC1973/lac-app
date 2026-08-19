import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCPF, validateCPF, formatPhone } from '@/lib/utils'
import {
  Plus, Sun, Pencil, Trash2, X, ChevronDown, ChevronUp,
  Cpu, Upload, FileText, Eye, SunMedium,
} from 'lucide-react'

const MARCAS_INVERSOR = ['Growatt', 'Solis', 'SAJ', 'Fronius', 'Candian', 'Deye']

const TIPOS_DOC_USINA = [
  { key: 'identidade_cnh', label: 'Identidade ou CNH' },
  { key: 'comprovante_endereco', label: 'Comprovante de Endereco' },
  { key: 'projeto_aprovacao', label: 'Projeto de Aprovacao' },
  { key: 'vistoria_energisa', label: 'Vistoria da Energisa' },
  { key: 'nota_fiscal', label: 'Nota Fiscal de Equipamento' },
  { key: 'certificado_garantia', label: 'Certificado de Garantia' },
]

export default function Usinas() {
  const { hasPermission } = useAuth()
  const [usinas, setUsinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingUsina, setEditingUsina] = useState(null)
  const [expandedUsina, setExpandedUsina] = useState(null)

  const canCreate = hasPermission('usinas', 'criar')
  const canEdit = hasPermission('usinas', 'editar')
  const canDelete = hasPermission('usinas', 'excluir')

  useEffect(() => { loadUsinas() }, [])

  async function loadUsinas() {
    setLoading(true)
    try {
      const { data } = await api.get('/usinas/')
      setUsinas(data)
    } catch (err) {
      console.error('Erro ao carregar usinas:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id, nome) {
    if (!confirm('Tem certeza que deseja excluir "' + nome + '"? Todos os dados vinculados serao perdidos.')) return
    try {
      await api.delete('/usinas/' + id)
      await loadUsinas()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir')
    }
  }

  function handleEdit(usina) {
    setEditingUsina(usina)
    setShowForm(true)
  }

  function handleNew() {
    setEditingUsina(null)
    setShowForm(true)
  }

  function handleFormClose() {
    setShowForm(false)
    setEditingUsina(null)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Usinas Solares</h1>
          <p className="text-dark-500 text-sm mt-1">Gerencie suas usinas e inversores</p>
        </div>
        {canCreate && (
          <button
            onClick={handleNew}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
          >
            <Plus size={18} />
            Nova Usina
          </button>
        )}
      </div>

      {showForm && (
        <UsinaForm usina={editingUsina} onClose={handleFormClose} onSaved={loadUsinas} />
      )}

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : usinas.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <Sun size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhuma usina cadastrada</p>
        </div>
      ) : (
        <div className="space-y-3">
          {usinas.map((usina) => {
            const isExpanded = expandedUsina === usina.id
            return (
              <div key={usina.id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
                <div
                  className="flex items-center justify-between px-5 py-4 cursor-pointer hover:bg-dark-50 transition"
                  onClick={() => setExpandedUsina(isExpanded ? null : usina.id)}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-solar-100 text-solar-700 flex items-center justify-center">
                      <Sun size={20} />
                    </div>
                    <div>
                      <p className="font-medium text-dark-900">{usina.nome}</p>
                      <p className="text-sm text-dark-500">
                        {usina.potencia_kwp ? usina.potencia_kwp + ' kWp' : 'Potencia nao definida'}
                        {usina.inversores?.length > 0 && ' - ' + usina.inversores.length + ' inversor(es)'}
                        {usina.placas?.length > 0 && ' - ' + usina.placas.length + ' placa(s)'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {canEdit && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleEdit(usina) }}
                        className="p-2 rounded-lg text-dark-400 hover:text-solar-600 hover:bg-dark-100 transition"
                      >
                        <Pencil size={18} />
                      </button>
                    )}
                    {canDelete && (
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(usina.id, usina.nome) }}
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
                    <h3 className="text-sm font-semibold text-dark-700 mt-4 mb-3">Proprietario</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      <Info label="Nome" value={usina.proprietario_nome} />
                      <Info label="CPF" value={usina.proprietario_cpf} />
                      <Info label="Celular" value={usina.proprietario_celular} />
                      <Info label="Identidade" value={usina.proprietario_identidade} />
                      <Info label="Endereco" value={usina.proprietario_endereco} />
                      <Info label="UC Poste" value={usina.uc_poste} />
                      <Info label="Potencia" value={usina.potencia_kwp ? usina.potencia_kwp + ' kWp' : null} />
                      <Info label="Dia Leitura" value={usina.data_leitura ? 'Dia ' + usina.data_leitura : null} />
                      <Info label="Inicio Operacao" value={usina.inicio_operacao} />
                    </div>

                    {usina.observacoes && (
                      <div className="mt-3">
                        <span className="text-xs text-dark-400">Observacoes</span>
                        <p className="text-sm text-dark-700 mt-0.5">{usina.observacoes}</p>
                      </div>
                    )}

                    <EngenheiroSection usina={usina} canEdit={canEdit} onSaved={loadUsinas} />

                    <div className="mt-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Cpu size={16} className="text-lac-600" />
                          <h3 className="text-sm font-semibold text-dark-700">Inversores</h3>
                        </div>
                        {canEdit && <InversorAddButton usinaId={usina.id} onSaved={loadUsinas} />}
                      </div>
                      {usina.inversores?.length > 0 ? (
                        <div className="space-y-2">
                          {usina.inversores.map((inv) => (
                            <InversorItem key={inv.id} inversor={inv} canEdit={canEdit} canDelete={canDelete} onSaved={loadUsinas} />
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-dark-400">Nenhum inversor cadastrado</p>
                      )}
                    </div>

                    <div className="mt-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <SunMedium size={16} className="text-solar-600" />
                          <h3 className="text-sm font-semibold text-dark-700">Placas Solares</h3>
                        </div>
                        {canEdit && <PlacaAddButton usinaId={usina.id} onSaved={loadUsinas} />}
                      </div>
                      {usina.placas?.length > 0 ? (
                        <div className="space-y-2">
                          {usina.placas.map((placa) => (
                            <PlacaItem key={placa.id} placa={placa} canEdit={canEdit} canDelete={canDelete} onSaved={loadUsinas} />
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-dark-400">Nenhuma placa cadastrada</p>
                      )}
                    </div>

                    <DocumentosSection usinaId={usina.id} canEdit={canEdit} canDelete={canDelete} />
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

function UsinaForm({ usina, onClose, onSaved }) {
  const isEditing = !!usina
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    nome: usina?.nome || '',
    proprietario_nome: usina?.proprietario_nome || '',
    proprietario_cpf: usina?.proprietario_cpf || '',
    proprietario_identidade: usina?.proprietario_identidade || '',
    proprietario_celular: usina?.proprietario_celular || '',
    proprietario_endereco: usina?.proprietario_endereco || '',
    uc_poste: usina?.uc_poste || '',
    potencia_kwp: usina?.potencia_kwp || '',
    data_leitura: usina?.data_leitura || '',
    inicio_operacao: usina?.inicio_operacao || '',
    observacoes: usina?.observacoes || '',
  })

  function handleChange(field, value) {
    setForm({ ...form, [field]: value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    const payload = { ...form }
    if (payload.potencia_kwp) payload.potencia_kwp = parseFloat(payload.potencia_kwp)
    if (payload.data_leitura) payload.data_leitura = parseInt(payload.data_leitura)
    Object.keys(payload).forEach((key) => {
      if (payload[key] === '' || payload[key] === null) delete payload[key]
    })
    try {
      if (isEditing) {
        await api.put('/usinas/' + usina.id, payload)
      } else {
        await api.post('/usinas/', payload)
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
      <div className="bg-white rounded-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold">{isEditing ? 'Editar Usina' : 'Nova Usina'}</h2>
          <button onClick={onClose} className="text-dark-400 hover:text-dark-600"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField label="Nome da Usina *" value={form.nome} onChange={(v) => handleChange('nome', v)} required />
          <div className="border-t border-dark-200 pt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Proprietario</h3>
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Nome" value={form.proprietario_nome} onChange={(v) => handleChange('proprietario_nome', v)} />
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">CPF</label>
                <input type="text" value={form.proprietario_cpf}
                  onChange={(e) => handleChange('proprietario_cpf', formatCPF(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  placeholder="000.000.000-00" />
                {form.proprietario_cpf && form.proprietario_cpf.replace(/\D/g, '').length === 11 && !validateCPF(form.proprietario_cpf) && (
                  <p className="text-xs text-red-500 mt-1">CPF invalido</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <FormField label="Identidade" value={form.proprietario_identidade} onChange={(v) => handleChange('proprietario_identidade', v)} />
              <div>
                <label className="block text-sm font-medium text-dark-600 mb-1">Celular</label>
                <input type="text" value={form.proprietario_celular}
                  onChange={(e) => handleChange('proprietario_celular', formatPhone(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
                  placeholder="(65) 99999-9999" />
              </div>
            </div>
            <div className="mt-4">
              <FormField label="Endereco" value={form.proprietario_endereco} onChange={(v) => handleChange('proprietario_endereco', v)} />
            </div>
          </div>
          <div className="border-t border-dark-200 pt-4">
            <h3 className="text-sm font-semibold text-dark-700 mb-3">Dados da Usina</h3>
            <div className="grid grid-cols-3 gap-4">
              <FormField label="UC Poste" value={form.uc_poste} onChange={(v) => handleChange('uc_poste', v)} />
              <FormField label="Potencia (kWp)" value={form.potencia_kwp} onChange={(v) => handleChange('potencia_kwp', v)} type="number" />
              <FormField label="Dia Leitura" value={form.data_leitura} onChange={(v) => handleChange('data_leitura', v)} type="number" />
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <FormField label="Inicio Operacao" value={form.inicio_operacao} onChange={(v) => handleChange('inicio_operacao', v)} type="date" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-dark-600 mb-1">Observacoes</label>
            <textarea value={form.observacoes} onChange={(e) => handleChange('observacoes', e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50 resize-none" rows={3} />
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

function FormField({ label, value, onChange, type = 'text', placeholder, required }) {
  return (
    <div>
      <label className="block text-sm font-medium text-dark-600 mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
        placeholder={placeholder} required={required} step={type === 'number' ? 'any' : undefined} />
    </div>
  )
}

function EngenheiroSection({ usina, canEdit, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [nome, setNome] = useState(usina.engenheiro_nome || '')
  const [crea, setCrea] = useState(usina.engenheiro_crea || '')
  const [saving, setSaving] = useState(false)
  const [docs, setDocs] = useState([])
  const [uploading, setUploading] = useState(false)

  useEffect(() => { loadDocs() }, [usina.id])

  async function loadDocs() {
    try {
      const { data } = await api.get('/documentos/?usina_id=' + usina.id)
      setDocs(data.filter((d) => d.tipo === 'crea'))
    } catch (err) {
      console.error('Erro:', err)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.put('/usinas/' + usina.id, { engenheiro_nome: nome || null, engenheiro_crea: crea || null })
      setEditing(false)
      await onSaved()
    } catch (err) {
      alert('Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  async function handleUploadCrea(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tipo', 'crea')
      formData.append('usina_id', usina.id)
      await api.post('/documentos/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      await loadDocs()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro no upload')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleDeleteDoc(docId) {
    if (!confirm('Excluir documento do CREA?')) return
    try {
      await api.delete('/documentos/' + docId)
      await loadDocs()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-dark-700">Engenheiro Responsavel</h3>
        {canEdit && !editing && (
          <button onClick={() => setEditing(true)} className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
            <Pencil size={14} /> Editar
          </button>
        )}
      </div>
      {editing ? (
        <div className="space-y-3 bg-dark-50 rounded-lg p-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-dark-500 mb-1">Nome do Engenheiro</label>
              <input type="text" value={nome} onChange={(e) => setNome(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
            </div>
            <div>
              <label className="block text-xs font-medium text-dark-500 mb-1">Numero CREA</label>
              <input type="text" value={crea} onChange={(e) => setCrea(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={saving}
              className="px-4 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
            <button onClick={() => setEditing(false)}
              className="px-4 py-1.5 rounded-lg border border-dark-300 text-sm text-dark-600 hover:bg-dark-100 transition">Cancelar</button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <Info label="Nome" value={usina.engenheiro_nome} />
          <Info label="CREA" value={usina.engenheiro_crea} />
        </div>
      )}
      <div className="mt-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-dark-500">Documento CREA</span>
          {canEdit && (
            <label className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-xs font-medium cursor-pointer hover:bg-solar-600 transition">
              <Upload size={14} />
              {uploading ? 'Enviando...' : 'Upload CREA'}
              <input type="file" className="hidden" onChange={handleUploadCrea} disabled={uploading} accept=".pdf,.jpg,.jpeg,.png" />
            </label>
          )}
        </div>
        {docs.length > 0 ? (
          <div className="space-y-2">
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileText size={16} className="text-dark-500" />
                  <span className="text-sm text-dark-700">{doc.nome_arquivo}</span>
                </div>
                <div className="flex items-center gap-1">
                  <a href={doc.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded text-dark-400 hover:text-solar-600 transition"><Eye size={14} /></a>
                  {canEdit && (
                    <button onClick={() => handleDeleteDoc(doc.id)} className="p-1.5 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-dark-400">Nenhum documento CREA enviado</p>
        )}
      </div>
    </div>
  )
}

function InversorAddButton({ usinaId, onSaved }) {
  const [show, setShow] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ marca: '', potencia_kwp: '', tipo: 'principal', ordem: 1 })

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/inversores/' + usinaId, { ...form, potencia_kwp: parseFloat(form.potencia_kwp), ordem: parseInt(form.ordem) })
      setShow(false)
      setForm({ marca: '', potencia_kwp: '', tipo: 'principal', ordem: 1 })
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao adicionar inversor')
    } finally {
      setSaving(false)
    }
  }

  if (!show) {
    return (
      <button onClick={() => setShow(true)} className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
        <Plus size={14} /> Adicionar
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <select value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })}
        className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-solar-500/50" required>
        <option value="">Marca</option>
        {MARCAS_INVERSOR.map((m) => (<option key={m} value={m}>{m}</option>))}
      </select>
      <input type="number" value={form.potencia_kwp} onChange={(e) => setForm({ ...form, potencia_kwp: e.target.value })}
        placeholder="kWp" className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-20 focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" required />
      <button type="submit" disabled={saving} className="px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
        {saving ? '...' : 'OK'}
      </button>
      <button type="button" onClick={() => setShow(false)} className="text-dark-400 hover:text-dark-600"><X size={16} /></button>
    </form>
  )
}

function InversorItem({ inversor, canEdit, canDelete, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ marca: inversor.marca, potencia_kwp: inversor.potencia_kwp, tipo: inversor.tipo, ordem: inversor.ordem })

  async function handleSave() {
    try {
      await api.put('/inversores/' + inversor.id, { ...form, potencia_kwp: parseFloat(form.potencia_kwp), ordem: parseInt(form.ordem) })
      setEditing(false)
      await onSaved()
    } catch (err) {
      alert('Erro ao salvar')
    }
  }

  async function handleDelete() {
    if (!confirm('Excluir inversor ' + inversor.marca + '?')) return
    try {
      await api.delete('/inversores/' + inversor.id)
      await onSaved()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  if (editing) {
    return (
      <div className="flex items-center gap-2 p-2 bg-dark-50 rounded-lg">
        <select value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })}
          className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-solar-500/50">
          {MARCAS_INVERSOR.map((m) => (<option key={m} value={m}>{m}</option>))}
        </select>
        <input type="number" value={form.potencia_kwp} onChange={(e) => setForm({ ...form, potencia_kwp: e.target.value })}
          className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-20 focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" />
        <button onClick={handleSave} className="px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium">Salvar</button>
        <button onClick={() => setEditing(false)} className="text-dark-400 hover:text-dark-600"><X size={16} /></button>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
      <div className="flex items-center gap-3">
        <Cpu size={16} className="text-lac-500" />
        <span className="text-sm font-medium text-dark-700">{inversor.marca}</span>
        <span className="text-sm text-dark-500">{inversor.potencia_kwp} kWp</span>
        <span className="text-xs text-dark-400">({inversor.tipo})</span>
      </div>
      <div className="flex items-center gap-1">
        {canEdit && (<button onClick={() => setEditing(true)} className="p-1.5 rounded text-dark-400 hover:text-solar-600 transition"><Pencil size={14} /></button>)}
        {canDelete && (<button onClick={handleDelete} className="p-1.5 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>)}
      </div>
    </div>
  )
}

function PlacaAddButton({ usinaId, onSaved }) {
  const [show, setShow] = useState(false)
  const [saving, setSaving] = useState(false)
    const [form, setForm] = useState({ potencia_wp: '', quantidade: 1 })

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/placas/' + usinaId, { ...form, potencia_wp: parseFloat(form.potencia_wp), quantidade: parseInt(form.quantidade) })
      setShow(false)
      setForm({ marca: '', modelo: '', potencia_wp: '', quantidade: 1 })
      await onSaved()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao adicionar placa')
    } finally {
      setSaving(false)
    }
  }

  if (!show) {
    return (
      <button onClick={() => setShow(true)} className="text-xs text-solar-600 hover:text-solar-700 font-medium flex items-center gap-1">
        <Plus size={14} /> Adicionar
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input type="number" value={form.potencia_wp} onChange={(e) => setForm({ ...form, potencia_wp: e.target.value })}
        placeholder="Wp" className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-16 focus:outline-none focus:ring-2 focus:ring-solar-500/50" step="any" required />
      <input type="number" value={form.quantidade} onChange={(e) => setForm({ ...form, quantidade: e.target.value })}
        placeholder="Qtd" className="px-3 py-1.5 rounded-lg border border-dark-300 text-sm w-14 focus:outline-none focus:ring-2 focus:ring-solar-500/50" min="1" required />
      <button type="submit" disabled={saving} className="px-3 py-1.5 rounded-lg bg-solar-500 text-dark-900 text-sm font-medium hover:bg-solar-600 transition disabled:opacity-50">
        {saving ? '...' : 'OK'}
      </button>
      <button type="button" onClick={() => setShow(false)} className="text-dark-400 hover:text-dark-600"><X size={16} /></button>
    </form>
  )
}

function PlacaItem({ placa, canEdit, canDelete, onSaved }) {
  async function handleDelete() {
    if (!confirm('Excluir esta placa?')) return
    try {
      await api.delete('/placas/' + placa.id)
      await onSaved()
    } catch (err) {
      alert('Erro ao excluir')
    }
  }

  return (
    <div className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
      <div className="flex items-center gap-3">
        <SunMedium size={16} className="text-solar-500" />
        <span className="text-sm text-dark-500">{placa.potencia_wp} Wp</span>
        <span className="text-xs text-dark-400">x{placa.quantidade}</span>
        <span className="text-xs text-lac-600 font-medium">({((placa.potencia_wp * placa.quantidade) / 1000).toFixed(2)} kWp total)</span>
      </div>
      <div className="flex items-center gap-1">
        {canDelete && (<button onClick={handleDelete} className="p-1.5 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>)}
      </div>
    </div>
  )
}

function DocumentosSection({ usinaId, canEdit, canDelete }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [tipoUpload, setTipoUpload] = useState('')

  useEffect(() => { loadDocs() }, [usinaId])

  async function loadDocs() {
    setLoading(true)
    try {
      const { data } = await api.get('/documentos/?usina_id=' + usinaId)
      setDocs(data.filter((d) => d.tipo !== 'crea'))
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file || !tipoUpload) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('tipo', tipoUpload)
      formData.append('usina_id', usinaId)
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

  const tipoLabel = (tipo) => {
    const found = TIPOS_DOC_USINA.find((t) => t.key === tipo)
    return found ? found.label : tipo
  }

  return (
    <div className="mt-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-dark-600" />
          <h3 className="text-sm font-semibold text-dark-700">Documentos</h3>
        </div>
        {canEdit && (
          <div className="flex items-center gap-2">
            <select value={tipoUpload} onChange={(e) => setTipoUpload(e.target.value)}
              className="px-2 py-1.5 rounded-lg border border-dark-300 text-xs focus:outline-none focus:ring-2 focus:ring-solar-500/50">
              <option value="">Tipo do documento</option>
              {TIPOS_DOC_USINA.map((t) => (<option key={t.key} value={t.key}>{t.label}</option>))}
            </select>
            <label className={cn(
              'flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition',
              tipoUpload ? 'bg-solar-500 text-dark-900 hover:bg-solar-600' : 'bg-dark-200 text-dark-400 cursor-not-allowed'
            )}>
              <Upload size={14} />
              {uploading ? 'Enviando...' : 'Upload'}
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
          {docs.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-2 bg-dark-50 rounded-lg">
              <div className="flex items-center gap-3">
                <FileText size={16} className="text-dark-500" />
                <div>
                  <span className="text-sm font-medium text-dark-700">{doc.nome_arquivo}</span>
                  <span className="text-xs text-dark-400 ml-2">{tipoLabel(doc.tipo)}</span>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <a href={doc.url} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded text-dark-400 hover:text-solar-600 transition"><Eye size={14} /></a>
                {canDelete && (<button onClick={() => handleDelete(doc.id)} className="p-1.5 rounded text-dark-400 hover:text-red-500 transition"><Trash2 size={14} /></button>)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
