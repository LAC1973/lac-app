import { useState, useEffect } from 'react'
import api from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { DollarSign, ChevronLeft, ChevronRight } from 'lucide-react'

const MESES_CURTO = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

export default function DRE() {
  const [dados, setDados] = useState(null)
  const [ano, setAno] = useState(new Date().getFullYear())
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadDRE() }, [ano])

  async function loadDRE() {
    setLoading(true)
    try {
      const { data } = await api.get('/relatorios/dre?ano=' + ano)
      setDados(data)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  function somaAno(campo) {
    if (!dados) return 0
    return Object.values(dados).reduce((sum, m) => sum + (m[campo] || 0), 0)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">DRE</h1>
          <p className="text-dark-500 text-sm mt-1">Demonstrativo de Resultado do Exercicio</p>
        </div>
      </div>

      <div className="flex items-center justify-center gap-4 mb-6">
        <button onClick={() => setAno(ano - 1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronLeft size={20} /></button>
        <h2 className="text-lg font-semibold text-dark-900 w-24 text-center">{ano}</h2>
        <button onClick={() => setAno(ano + 1)} className="p-2 rounded-lg hover:bg-dark-200 transition"><ChevronRight size={20} /></button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : !dados ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <DollarSign size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Nenhum dado encontrado</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-200 bg-dark-50">
                  <th className="text-left py-3 px-4 font-medium text-dark-600 sticky left-0 bg-dark-50 w-48"></th>
                  {MESES_CURTO.slice(1).map((m, i) => (
                    <th key={i} className="text-right py-3 px-3 font-medium text-dark-600">{m}</th>
                  ))}
                  <th className="text-right py-3 px-4 font-bold text-dark-800">Total</th>
                </tr>
              </thead>
              <tbody>
                <DRERow label="A - Receita Bruta" dados={dados} campo="receita_bruta" total={somaAno('receita_bruta')} bold color="text-dark-900" bg="bg-green-50" />
                <DRERow label="B - Agregados" dados={dados} campo="agregados" total={somaAno('agregados')} color="text-red-600" prefix="-" />
                <DRERow label="C - Receita Operacional" dados={dados} campo="receita_operacional" total={somaAno('receita_operacional')} bold color="text-dark-900" bg="bg-green-50" />
                <tr><td colSpan={14} className="py-1"></td></tr>
                <DRERow label="E - Despesas Operacionais" dados={dados} campo="despesas" total={somaAno('despesas')} color="text-red-600" prefix="-" />
                <DRERow label="F - Financiamentos" dados={dados} campo="financiamentos" total={somaAno('financiamentos')} color="text-red-600" prefix="-" />
                <tr><td colSpan={14} className="py-1"></td></tr>
                <DRERow label="G - Resultado Operacional" dados={dados} campo="resultado_operacional" total={somaAno('resultado_operacional')} bold color="text-lac-700" bg="bg-lac-50" />
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function DRERow({ label, dados, campo, total, bold, color, bg, prefix }) {
  return (
    <tr className={bg || ''}>
      <td className={'py-2.5 px-4 sticky left-0 ' + (bg || 'bg-white') + ' ' + (bold ? 'font-semibold' : '') + ' text-dark-700 whitespace-nowrap'}>
        {label}
      </td>
      {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
        const val = dados[m]?.[campo] || 0
        return (
          <td key={m} className={'py-2.5 px-3 text-right ' + (bold ? 'font-semibold ' : '') + (color || 'text-dark-700')}>
            {val ? (prefix || '') + formatCurrency(val) : '-'}
          </td>
        )
      })}
      <td className={'py-2.5 px-4 text-right font-bold ' + (color || 'text-dark-900')}>
        {(prefix || '') + formatCurrency(total)}
      </td>
    </tr>
  )
}