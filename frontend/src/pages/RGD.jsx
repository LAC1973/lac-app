import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { BarChart3, ChevronLeft, ChevronRight } from 'lucide-react'

const MESES_CURTO = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export default function RGD() {
  const [dados, setDados] = useState([])
  const [ano, setAno] = useState(new Date().getFullYear())
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadRGD() }, [ano])

  async function loadRGD() {
    setLoading(true)
    try {
      const { data } = await api.get('/relatorios/rgd?ano=' + ano)
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
          <h1 className="text-2xl font-bold">RGD</h1>
          <p className="text-dark-500 text-sm mt-1">Relatorio Gerencial de Desempenho</p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 mb-6">
        <button onClick={() => setAno(ano - 1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronLeft size={20} /></button>
        <h2 className="text-lg font-semibold text-dark-900 w-24 text-center">{ano}</h2>
        <button onClick={() => setAno(ano + 1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronRight size={20} /></button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : dados.length === 0 ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <BarChart3 size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum dado encontrado para {ano}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {dados.map((usina) => (
            <div key={usina.usina_id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-dark-100 flex items-center gap-3">
                <BarChart3 size={18} className="text-solar-600" />
                <h2 className="font-semibold text-dark-900">{usina.usina_nome}</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-dark-200 bg-dark-50">
                      <th className="text-left py-2 px-3 font-medium text-dark-600 sticky left-0 bg-dark-50">Cliente</th>
                      {MESES_CURTO.slice(1).map((m, i) => (
                        <th key={i} className="text-right py-2 px-2 font-medium text-dark-600" colSpan={2}>{m}</th>
                      ))}
                      <th className="text-right py-2 px-3 font-medium text-dark-700">Total</th>
                    </tr>
                    <tr className="border-b border-dark-200 bg-dark-50">
                      <th className="sticky left-0 bg-dark-50"></th>
                      {Array.from({ length: 12 }).map((_, i) => (
                        <><th key={'k' + i} className="text-right py-1 px-1 font-normal text-dark-400 text-[10px]">kWh</th>
                        <th key={'v' + i} className="text-right py-1 px-1 font-normal text-dark-400 text-[10px]">R$</th></>
                      ))}
                      <th className="text-right py-1 px-3 font-normal text-dark-400 text-[10px]">R$</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usina.clientes.map((c) => (
                      <tr key={c.cliente_id} className="border-b border-dark-100 hover:bg-dark-50">
                        <td className="py-2 px-3 text-dark-900 font-medium sticky left-0 bg-white whitespace-nowrap">{c.nome_uc || c.nome}</td>
                        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                          <><td key={'k' + m} className="py-2 px-1 text-right text-dark-600">{c.meses[m]?.kwh ? c.meses[m].kwh.toFixed(0) : ''}</td>
                          <td key={'v' + m} className="py-2 px-1 text-right text-dark-600">{c.meses[m]?.valor ? c.meses[m].valor.toFixed(0) : ''}</td></>
                        ))}
                        <td className="py-2 px-3 text-right font-semibold text-dark-900">{formatCurrency(c.total_valor)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-solar-50 font-semibold">
                      <td className="py-2 px-3 text-dark-700 sticky left-0 bg-solar-50">Total</td>
                      {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                        <><td key={'k' + m} className="py-2 px-1 text-right text-dark-700">{usina.totais_mes[m]?.kwh ? usina.totais_mes[m].kwh.toFixed(0) : ''}</td>
                        <td key={'v' + m} className="py-2 px-1 text-right text-solar-700">{usina.totais_mes[m]?.valor ? usina.totais_mes[m].valor.toFixed(0) : ''}</td></>
                      ))}
                      <td className="py-2 px-3 text-right text-solar-700">{formatCurrency(usina.clientes.reduce((s, c) => s + c.total_valor, 0))}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}