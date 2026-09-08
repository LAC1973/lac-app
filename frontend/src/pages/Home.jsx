import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/lib/api'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import {
  Sun, FileText, DollarSign, TrendingUp, TrendingDown,
  CalendarClock, AlertTriangle, CheckCircle2, PieChart,
  Zap, HeartHandshake, Users,
} from 'lucide-react'

export default function Home() {
  const { profile } = useAuth()
  const [dados, setDados] = useState(null)
  const [loading, setLoading] = useState(true)

  async function loadDashboard() {
    setLoading(true)
    try {
      const { data } = await api.get('/dashboard/')
      setDados(data)
    } catch (err) {
      console.error('Erro ao carregar dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  const alertas = dados
    ? (dados.usinas_sem_producao?.length || 0) + (dados.percentuais_incompletos?.length || 0)
    : 0
  const hora = new Date().getHours()
  const saudacao =
    hora < 12 ? 'Bom dia' : hora < 18 ? 'Boa tarde' : 'Boa noite'
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dark-900">
          {saudacao}, {profile?.full_name?.split(' ')[0]}
        </h1>
        <p className="text-dark-500 mt-1">Visão geral das usinas solares</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-dark-400">Carregando...</div>
      ) : !dados ? (
        <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
          <Sun size={48} className="mx-auto mb-4 text-dark-300" />
          <p className="text-dark-500">Não foi possível carregar o dashboard</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <KpiCard
              label="Contas a Receber"
              value={formatCurrency(dados.contas_a_receber.valor_total)}
              sublabel={`${dados.contas_a_receber.quantidade} fatura(s) pendente(s)/atrasada(s)`}
              icon={FileText}
              color="solar"
            />
            <KpiCard
              label="Receita do Mês"
              value={formatCurrency(dados.receita.mes_atual)}
              sublabel={<Variacao variacao={dados.receita.variacao_pct} />}
              icon={DollarSign}
              color="lac"
            />
            <KpiCard
              label="Resultado do Mês"
              value={formatCurrency(dados.resultado_mes_atual.resultado_operacional)}
              sublabel={`Despesas: ${formatCurrency(dados.resultado_mes_atual.despesas + dados.resultado_mes_atual.financiamentos)}`}
              icon={PieChart}
              color="solar"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <KpiCard
              label="Produção do Mês"
              value={`${dados.producao.mes_atual_kwh.toLocaleString('pt-BR')} kWh`}
              sublabel={<Variacao variacao={dados.producao.variacao_pct} />}
              icon={Zap}
              color="lac"
            />
            <KpiCard
              label="Economia dos Clientes (Ano)"
              value={formatCurrency(dados.economia_acumulada_ano)}
              sublabel="Economia acumulada vs tarifa Energisa"
              icon={HeartHandshake}
              color="solar"
            />
            <KpiCard
              label="Usinas e Clientes"
              value={`${dados.contagens.usinas} usina(s)`}
              sublabel={`${dados.contagens.clientes_ativos} cliente(s) ativo(s)`}
              icon={Users}
              color="lac"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-dark-100 flex items-center gap-2">
                <CalendarClock size={18} className="text-solar-600" />
                <h2 className="font-semibold text-dark-900">Próximos Vencimentos (7 dias)</h2>
              </div>
              {dados.proximos_vencimentos.length === 0 ? (
                <p className="text-sm text-dark-400 p-5">Nenhuma fatura vencendo nos próximos 7 dias.</p>
              ) : (
                <div className="divide-y divide-dark-100">
                  {dados.proximos_vencimentos.map((f) => (
                    <div key={f.fatura_id} className="flex items-center justify-between px-5 py-3">
                      <div>
                        <p className="text-sm font-medium text-dark-700">{f.cliente_nome}</p>
                        <p className="text-xs text-dark-400">Vence em {formatDate(f.data_vencimento)}</p>
                      </div>
                      <span className="text-sm font-semibold text-dark-900">{formatCurrency(f.valor_final)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-dark-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-dark-100 flex items-center gap-2">
                <AlertTriangle size={18} className="text-solar-600" />
                <h2 className="font-semibold text-dark-900">Alertas Operacionais</h2>
              </div>
              {alertas === 0 ? (
                <div className="flex items-center gap-2 px-5 py-5 text-dark-500">
                  <CheckCircle2 size={18} className="text-green-500" />
                  <p className="text-sm">Tudo certo — nenhum alerta no momento.</p>
                </div>
              ) : (
                <div className="divide-y divide-dark-100">
                  {dados.usinas_sem_producao.map((u) => (
                    <div key={'prod-' + u.usina_id} className="flex items-center gap-3 px-5 py-3">
                      <AlertTriangle size={16} className="text-yellow-500 shrink-0" />
                      <p className="text-sm text-dark-700">
                        <span className="font-medium">{u.usina_nome}</span> sem produção lançada este mês
                      </p>
                    </div>
                  ))}
                  {dados.percentuais_incompletos.map((u) => (
                    <div key={'perc-' + u.usina_id} className="flex items-center gap-3 px-5 py-3">
                      <AlertTriangle size={16} className="text-red-500 shrink-0" />
                      <p className="text-sm text-dark-700">
                        <span className="font-medium">{u.usina_nome}</span> com percentuais somando{' '}
                        {u.soma_percentuais}% (deveria ser 100%)
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function KpiCard({ label, value, sublabel, icon: Icon, color }) {
  return (
    <div className="bg-white rounded-xl p-5 border border-dark-200 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-dark-500">{label}</span>
        <div className={cn(
          'w-9 h-9 rounded-lg flex items-center justify-center',
          color === 'solar' ? 'bg-solar-100 text-solar-700' : 'bg-lac-100 text-lac-700'
        )}>
          <Icon size={18} />
        </div>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {sublabel && <div className="text-xs text-dark-400 mt-1">{sublabel}</div>}
    </div>
  )
}

function Variacao({ variacao }) {
  if (variacao === null || variacao === undefined) {
    return <span>Sem dados do mês anterior</span>
  }
  const subiu = variacao >= 0
  return (
    <span className={cn('flex items-center gap-1', subiu ? 'text-green-600' : 'text-red-500')}>
      {subiu ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {Math.abs(variacao)}% vs mês anterior
    </span>
  )
}
