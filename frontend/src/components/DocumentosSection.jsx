import { useState, useEffect } from 'react'
import api, { dedupedGet } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Upload, FileText, Eye, Trash2 } from 'lucide-react'

export default function DocumentosSection({ entityIdField, entityId, tipos, canEdit, canDelete, excludeTipos = [] }) {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [tipoUpload, setTipoUpload] = useState('')

  useEffect(() => { loadDocs() }, [entityId])

  async function loadDocs() {
    setLoading(true)
    try {
      const { data } = await dedupedGet(`/documentos/?${entityIdField}=${entityId}`)
      setDocs(excludeTipos.length ? data.filter((d) => !excludeTipos.includes(d.tipo)) : data)
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
      formData.append(entityIdField, entityId)
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
    } catch {
      alert('Erro ao excluir')
    }
  }

  const tipoLabel = (tipo) => {
    const found = tipos.find((t) => t.key === tipo)
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
              {tipos.map((t) => (<option key={t.key} value={t.key}>{t.label}</option>))}
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
