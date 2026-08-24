import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import MonthPicker from '@/components/MonthPicker'
import { Zap, ChevronLeft, ChevronRight, Check, BarChart3 } from 'lucide-react'

export default function Producao() {
  const { hasPermission } = useAuth()
  const [data, setData] = useState(todayStr())
  const [usinas, setUsinas] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [valores, setValores] = useState({})
  const [view, setView] = useState('diario') // 'diario' ou 'mensal'
  const [mensal, setMensal] = useState([])
  const [mesMensal, setMesMensal] = useState({ ano: new Date().getFullYear(), mes: new Date().getMonth() + 1 })
  const [usinasFiltro, setUsinasFiltro] = useState([])
  const [filtroUsina, setFiltroUsina] = useState('')

  const canCreate = hasPermission('producao', 'criar')

  useEffect(() => { loadDia() }, [data])
  useEffect(() => { if (view === 'mensal') loadMensal() }, [view, mesMensal])
  useEffect(() => {
    api.get('/usinas/').then(({ data }) => setUsinasFiltro(data)).catch((err) => console.error('Erro:', err))
  }, [])

  function todayStr() {
    const d = new Date()
    return d.toISOString().split('T')[0]
  }

  function changeDay(offset) {
    const d = new Date(data + 'T12:00:00')
    d.setDate(d.getDate() + offset)
    const str = d.toISOString().split('T')[0]
    if (str > todayStr()) return
    setData(str)
  }

  async function loadDia() {
    setLoading(true)
    setSaved(false)
    try {
      const { data: result } = await api.get(`/producao/dia?data=${data}`)
      setUsinas(result)

      const vals = {}
      result.forEach((usina) => {
        usina.inversores.forEach((inv) => {
          vals[inv.inversor_id] = inv.producao_kwh !== null ? String(inv.producao_kwh) : ''
        })
      })
      setValores(vals)
    } catch (err) {
      console.error('Erro:', err)
    } finally {
      setLoading(false)
    }
  }

  async function loadMensal() {
    try {
      const { data: result } = await api.get(`/producao/mensal?ano=${mesMensal.ano}&mes=${mesMensal.mes}`)
      setMensal(result)
    } catch (err) {
      console.error('Erro:', err)
    }
  }

  function handleChange(inversorId, value) {
    setValores({ ...valores, [inversorId]: value })
    setSaved(false)
  }

  async function handleSave() {
    setSaving(true)
    try {
      const registros = Object.entries(valores)
        .filter(([_, v]) => v !== '' && v !== null)
        .map(([inversorId, kwh]) => ({
          inversor_id: parseInt(inversorId),
          data: data,
          producao_kwh: parseFloat(kwh),
        }))

      if (registros.length === 0) {
        alert('Preencha pelo menos um inversor')
        setSaving(false)
        return
      }

      await api.post('/producao/', { registros })
      setSaved(true)
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  function changeMes(offset) {
    setMesMensal((prev) => {
      let m = prev.mes + offset
      let a = prev.ano
      if (m > 12) { m = 1; a++ }
      if (m < 1) { m = 12; a-- }
      return { ano: a, mes: m }
    })
  }

  const dataFormatada = new Date(data + 'T12:00:00').toLocaleDateString('pt-BR', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric'
  })

  const usinasVisiveis = filtroUsina ? usinas.filter((u) => String(u.usina_id) === filtroUsina) : usinas
  const totalFiltrado = usinasVisiveis.reduce(
    (sum, u) => sum + u.inversores.reduce((s, inv) => s + (parseFloat(valores[inv.inversor_id]) || 0), 0),
    0
  )

  const mensalVisivel = filtroUsina ? mensal.filter((u) => String(u.usina_id) === filtroUsina) : mensal

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Produção Diária</h1>
          <p className="text-dark-500 text-sm mt-1">Registro de produção dos inversores</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView('diario')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition',
              view === 'diario' ? 'bg-solar-500 text-dark-900' : 'bg-dark-200 text-dark-600 hover:bg-dark-300'
            )}
          >
            <Zap size={16} className="inline mr-1" />
            Diário
          </button>
          <button
            onClick={() => setView('mensal')}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition',
              view === 'mensal' ? 'bg-solar-500 text-dark-900' : 'bg-dark-200 text-dark-600 hover:bg-dark-300'
            )}
          >
            <BarChart3 size={16} className="inline mr-1" />
            Mensal
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-6">
        <select
          value={filtroUsina}
          onChange={(e) => setFiltroUsina(e.target.value)}
          className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
        >
          <option value="">Todas as usinas</option>
          {usinasFiltro.map((u) => (<option key={u.id} value={u.id}>{u.nome}</option>))}
        </select>
      </div>

      {view === 'diario' ? (
        <>
          {/* Seletor de data */}
          <div className="flex items-center justify-center gap-4 mb-6">
            <button onClick={() => changeDay(-1)} className="p-2 rounded-lg hover:bg-dark-200 transition">
              <ChevronLeft size={20} />
            </button>
            <div className="text-center">
              <input
                type="date"
                value={data}
                max={todayStr()}
                onChange={(e) => setData(e.target.value)}
                className="px-4 py-2 rounded-lg border border-dark-300 text-sm focus:outline-none focus:ring-2 focus:ring-solar-500/50"
              />
              <p className="text-sm text-dark-500 mt-1 capitalize">{dataFormatada}</p>
            </div>
            <button
              onClick={() => changeDay(1)}
              disabled={data >= todayStr()}
              className="p-2 rounded-lg hover:bg-dark-200 transition disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight size={20} />
            </button>
          </div>

          {loading ? (
            <div className="text-center py-12 text-dark-400">Carregando...</div>
          ) : usinas.length === 0 ? (
            <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
              <Zap size={48} className="mx-auto mb-4 text-dark-300" />
              <p className="text-dark-500">Nenhuma usina com inversores cadastrados</p>
            </div>
          ) : (
            <>
              <div className="space-y-4">
                {usinasVisiveis.map((usina) => {
                  const totalUsina = usina.inversores.reduce(
                    (sum, inv) => sum + (parseFloat(valores[inv.inversor_id]) || 0), 0
                  )
                  return (
                    <div key={usina.usina_id} className="bg-white rounded-xl border border-dark-200 shadow-sm p-5">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-solar-100 text-solar-700 flex items-center justify-center">
                            <Zap size={18} />
                          </div>
                          <h2 className="font-semibold text-dark-900">{usina.usina_nome}</h2>
                        </div>
                        <span className="text-sm font-bold text-solar-600">{totalUsina.toFixed(1)} kWh</span>
                      </div>

                      <div className="space-y-3">
                        {usina.inversores.map((inv) => (
                          <div key={inv.inversor_id} className="flex items-center gap-4">
                            <div className="flex-1">
                              <span className="text-sm text-dark-700">{inv.marca}</span>
                              <span className="text-xs text-dark-400 ml-2">{inv.potencia_kwp} kWp</span>
                            </div>
                            <div className="relative w-32">
                              <input
                                type="number"
                                value={valores[inv.inversor_id] || ''}
                                onChange={(e) => handleChange(inv.inversor_id, e.target.value)}
                                placeholder="0.0"
                                step="any"
                                min="0"
                                disabled={!canCreate}
                                className="w-full px-3 py-2 rounded-lg border border-dark-300 text-sm text-right focus:outline-none focus:ring-2 focus:ring-solar-500/50 disabled:bg-dark-100 disabled:cursor-not-allowed"
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-dark-400 pointer-events-none">kWh</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Footer com total e botão salvar */}
              <div className="sticky bottom-0 mt-4 bg-white rounded-xl border border-dark-200 shadow-lg p-4 flex items-center justify-between">
                <div>
                  {filtroUsina ? (
                    <>
                      <span className="text-sm text-dark-500">Total do dia</span>
                      <p className="text-xl font-bold text-dark-900">{totalFiltrado.toFixed(1)} kWh</p>
                    </>
                  ) : (
                    <span className="text-sm text-dark-400">Selecione uma usina no filtro para ver o total</span>
                  )}
                </div>
                {canCreate && (
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className={cn(
                      'flex items-center gap-2 px-6 py-2.5 rounded-lg font-semibold text-sm transition',
                      saved
                        ? 'bg-lac-500 text-white'
                        : 'bg-solar-500 hover:bg-solar-600 text-dark-900'
                    )}
                  >
                    {saving ? 'Salvando...' : saved ? (
                      <><Check size={18} /> Salvo</>
                    ) : (
                      'Salvar Produção'
                    )}
                  </button>
                )}
              </div>
            </>
          )}
        </>
      ) : (
        /* Visão mensal */
        <>
          <MonthPicker mes={mesMensal.mes} ano={mesMensal.ano} onPrev={() => changeMes(-1)} onNext={() => changeMes(1)} />

          {mensalVisivel.length === 0 ? (
            <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
              <BarChart3 size={48} className="mx-auto mb-4 text-dark-300" />
              <p className="text-dark-500">Nenhum dado de produção neste mês</p>
            </div>
          ) : (
            <div className="space-y-4">
              {mensalVisivel.map((usina) => (
                <div key={usina.usina_id} className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-4 border-b border-dark-100">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-solar-100 text-solar-700 flex items-center justify-center">
                        <Zap size={18} />
                      </div>
                      <h2 className="font-semibold text-dark-900">{usina.usina_nome}</h2>
                    </div>
                    <span className="text-sm font-bold text-solar-600">{usina.total_mes?.toFixed(1)} kWh</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-dark-200 bg-dark-50">
                          <th className="text-left py-2 px-3 font-medium text-dark-600 sticky left-0 bg-dark-50">Dia</th>
                          {usina.inversores?.map((inv) => (
                            <th key={inv.id} className="text-right py-2 px-3 font-medium text-dark-600">
                              {inv.marca}
                            </th>
                          ))}
                          <th className="text-right py-2 px-3 font-medium text-dark-700">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {usina.dias?.map((dia) => (
                          <tr key={dia.data} className="border-b border-dark-100 hover:bg-dark-50">
                            <td className="py-2 px-3 text-dark-700 sticky left-0 bg-white">
                              {new Date(dia.data + 'T12:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                            </td>
                            {usina.inversores?.map((inv) => (
                              <td key={inv.id} className="text-right py-2 px-3 text-dark-600">
                                {dia.inversores[inv.id]?.toFixed(1) || '—'}
                              </td>
                            ))}
                            <td className="text-right py-2 px-3 font-medium text-dark-900">
                              {dia.total.toFixed(1)}
                            </td>
                          </tr>
                        ))}
                        {usina.dias?.length === 0 && (
                          <tr>
                            <td colSpan={usina.inversores.length + 2} className="text-center py-6 text-dark-400">
                              Sem dados neste mês
                            </td>
                          </tr>
                        )}
                      </tbody>
                      {usina.dias?.length > 0 && (
                        <tfoot>
                          <tr className="bg-solar-50 font-semibold">
                            <td className="py-2 px-3 text-dark-700 sticky left-0 bg-solar-50">Total</td>
                            {usina.inversores?.map((inv) => {
                              const total = usina.dias.reduce((sum, d) => sum + (d.inversores[inv.id] || 0), 0)
                              return (
                                <td key={inv.id} className="text-right py-2 px-3 text-dark-700">
                                  {total.toFixed(1)}
                                </td>
                              )
                            })}
                            <td className="text-right py-2 px-3 text-solar-700">{usina.total_mes?.toFixed(1)}</td>
                          </tr>
                        </tfoot>
                      )}
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}