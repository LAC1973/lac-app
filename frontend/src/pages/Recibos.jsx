import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCurrency, whatsappUrl } from '@/lib/utils'
import { NOMES_MES } from '@/lib/meses'
import MonthPicker from '@/components/MonthPicker'
import {
  Plus, Receipt, Trash2, X, Download, MessageCircle,
} from 'lucide-react'

export default function Recibos() {
  const { hasPermission } = useAuth()
  const [recibos, setRecibos] = useState([])
  const [loading, setLoading] = useState(true)
  const [mesRef, setMesRef] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
  })
  const [showGerar, setShowGerar] = useState(false)
  const [gerando, setGerando] = useState(false)

  const canCreate = hasPermission('recibos', 'criar')
  const canDelete = hasPermission('recibos', 'excluir')

  useEffect(() => { loadRecibos() }, [mesRef])

  async function loadRecibos() {
    setLoading(true)
    try {
      const { data } = await api.get(`/recibos/?mes_referencia=${mesRef}`)
      setRecibos(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleGerarLote() {
    setGerando(true)
    try {
      const { data } = await api.post(`/recibos/gerar-lote?mes_referencia=${mesRef}`)
      alert(data.message)
      setShowGerar(false)
      await loadRecibos()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao gerar recibos')
    } finally {
      setGerando(false)
    }
  }

  async function handleDownloadPDF(reciboId, clienteNome) {
    try {
      const response = await api.get(`/recibos/pdf/${reciboId}`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `recibo_${clienteNome.replace(/ /g, '_')}.pdf`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      alert('Erro ao baixar PDF')
    }
  }

  async function handleWhatsApp(recibo) {
    const cliente = recibo.clientes
    if (!cliente?.celular) {
      alert('Cliente sem numero de celular cadastrado')
      return
    }

    // Primeiro baixa o PDF
    await handleDownloadPDF(recibo.id, cliente.nome)

    // Monta mensagem
    const mesNum = parseInt(mesRef.split('-')[1])
    const ano = mesRef.split('-')[0]

    const mensagem = `Ola ${cliente.nome.split(' ')[0]}, segue o recibo de energia solar referente a ${NOMES_MES[mesNum]}/${ano}.\n\nValor: ${formatCurrency(recibo.valor_pago)}\n\nLAC Solar Ltda`

    const url = whatsappUrl(cliente.celular, mensagem)
    window.open(url, '_blank')
  }

  async function handleDelete(reciboId) {
    if (!confirm('Excluir este recibo?')) return
    try {
      await api.delete(`/recibos/${reciboId}`)
      await loadRecibos()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro')
    }
  }

  function changeMes(offset) {
    const d = new Date(mesRef + 'T12:00:00')
    d.setMonth(d.getMonth() + offset)
    setMesRef(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`)
  }

  const mesAtual = parseInt(mesRef.split('-')[1])
  const anoAtual = parseInt(mesRef.split('-')[0])

  const totalRecibos = recibos.reduce((sum, r) => sum + (r.valor_pago || 0), 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Recibos</h1>
          <p className="text-dark-500 text-sm mt-1">Recibos dos clientes com envio via WhatsApp</p>
        </div>
        {canCreate && (
          <button
            onClick={() => setShowGerar(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
          >
            <Plus size={18} />
            Gerar Recibos do Mes
          </button>
        )}
      </div>

      {/* Seletor de mes */}
      <MonthPicker mes={mesAtual} ano={anoAtual} onPrev={() => changeMes(-1)} onNext={() => changeMes(1)} />

      {/* Resumo */}
      <div className="bg-white rounded-xl p-4 border border-dark-200 shadow-sm mb-4">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm text-dark-500">Total de recibos no mes</span>
            <p className="text-xl font-bold">{formatCurrency(totalRecibos)}</p>
          </div>
          <span className="text-sm text-dark-400">{recibos.length} recibo(s)</span>
        </div>
      </div>

      {/* Modal gerar em lote */}
      {showGerar && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold">Gerar Recibos</h2>
              <button onClick={() => setShowGerar(false)} className="text-dark-400 hover:text-dark-600">
                <X size={20} />
              </button>
            </div>
            <p className="text-sm text-dark-600 mb-4">
              Gerar recibos para todos os clientes com faturas <strong>pagas</strong> em {NOMES_MES[mesAtual]} {anoAtual}?
            </p>
            <p className="text-xs text-dark-400 mb-4">
              Apenas clientes com faturas marcadas como "Paga" terao recibos gerados.
              Recibos ja existentes serao ignorados.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowGerar(false)}
                className="flex-1 py-2.5 rounded-lg border border-dark-300 text-sm font-medium text-dark-600 hover:bg-dark-50 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleGerarLote}
                disabled={gerando}
                className="flex-1 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 text-sm font-semibold transition disabled:opacity-50"
              >
                {gerando ? 'Gerando...' : 'Gerar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lista de recibos */}
      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : recibos.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <Receipt size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum recibo neste mes</p>
          <p className="text-sm text-dark-400 mt-1">Marque faturas como "Paga" e clique em "Gerar Recibos"</p>
        </div>
      ) : (
        <div className="space-y-3">
          {recibos.map((recibo) => {
            const cliente = recibo.clientes || {}
            return (
              <div key={recibo.id} className="bg-white rounded-xl border border-dark-200 shadow-sm p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-lac-100 text-lac-700 flex items-center justify-center text-sm font-bold">
                      {cliente.nome?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <p className="font-medium text-dark-900">{cliente.nome || 'Cliente'}</p>
                      <p className="text-sm text-dark-500">
                        {cliente.usinas?.nome || ''}
                        {recibo.forma_pagamento && ` - ${recibo.forma_pagamento}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-dark-900">{formatCurrency(recibo.valor_pago)}</p>
                    <p className="text-xs text-dark-400">
                      Pago em {recibo.data_pagamento ? new Date(recibo.data_pagamento + 'T12:00:00').toLocaleDateString('pt-BR') : '-'}
                    </p>
                  </div>
                </div>

                {/* Economia */}
                <div className="flex items-center gap-6 mt-3 pt-3 border-t border-dark-100">
                  <div>
                    <span className="text-xs text-dark-400">Economia no mes</span>
                    <p className="text-sm font-medium text-lac-600">{formatCurrency(recibo.economia_mensal)}</p>
                  </div>
                  <div>
                    <span className="text-xs text-dark-400">Economia no ano</span>
                    <p className="text-sm font-medium text-lac-600">{formatCurrency(recibo.economia_acumulada_ano)}</p>
                  </div>
                </div>

                {/* Acoes */}
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-dark-100">
                  <button
                    onClick={() => handleWhatsApp(recibo)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm font-medium transition"
                  >
                    <MessageCircle size={16} />
                    Enviar WhatsApp
                  </button>
                  <button
                    onClick={() => handleDownloadPDF(recibo.id, cliente.nome || 'recibo')}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-dark-800 hover:bg-dark-900 text-white text-sm font-medium transition"
                  >
                    <Download size={16} />
                    PDF
                  </button>
                  {canDelete && (
                    <button
                      onClick={() => handleDelete(recibo.id)}
                      className="p-2 rounded-lg text-dark-400 hover:text-red-500 hover:bg-dark-100 transition ml-auto"
                      title="Excluir"
                    >
                      <Trash2 size={18} />
                    </button>
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