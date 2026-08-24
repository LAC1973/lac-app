import { useState, useEffect } from 'react'
import api from '@/lib/api'
import { MESES_CURTO } from '@/lib/meses'
import YearPicker from '@/components/YearPicker'
import { Database } from 'lucide-react'

export default function SaldoACM() {
  const [dados, setDados] = useState([])
  const [usinas, setUsinas] = useState([])
  const [ano, setAno] = useState(new Date().getFullYear())
  const [filtroUsina, setFiltroUsina] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/usinas/').then(({ data }) => setUsinas(data))
  }, [])

  useEffect(() => { loadDados() }, [ano, filtroUsina])

  async function loadDados() {
    setLoading(true)
    try {
      var url = '/relatorios/saldo-acm?ano=' + ano
      if (filtroUsina) url += '&usina_id=' + filtroUsina
      const { data } = await api.get(url)
      setDados(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Saldo Acumulado</h1>
          <p className="text-dark-500 text-sm mt-1">Creditos de energia acumulados por cliente</p>
        </div>
      </div>

      <YearPicker ano={ano} onPrev={() => setAno(ano - 1)} onNext={() => setAno(ano + 1)} />

      <div className="flex items-center gap-3 mb-4">
        <select value={filtroUsina} onChange={(e) => setFiltroUsina(e.target.value)}
          className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50">
          <option value="">Todas as usinas</option>
          {usinas.map((u) => (<option key={u.id} value={u.id}>{u.nome}</option>))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : dados.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <Database size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum dado encontrado</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-200 bg-dark-50">
                  <th className="text-left py-3 px-3 font-medium text-dark-600 sticky left-0 bg-dark-50">Cliente</th>
                  <th className="text-left py-3 px-3 font-medium text-dark-600">Usina</th>
                  {MESES_CURTO.slice(1).map((m, i) => (
                    <th key={i} className="text-right py-3 px-3 font-medium text-dark-600">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dados.map((c) => (
                  <tr key={c.cliente_id} className="border-b border-dark-100 hover:bg-dark-50">
                    <td className="py-2 px-3 font-medium text-dark-900 sticky left-0 bg-white whitespace-nowrap">{c.nome_uc || c.nome}</td>
                    <td className="py-2 px-3 text-dark-500 text-xs">{c.usina_nome}</td>
                    {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                      <td key={m} className="py-2 px-3 text-right text-dark-700">
                        {c.meses[m] != null ? c.meses[m].toLocaleString('pt-BR') : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}