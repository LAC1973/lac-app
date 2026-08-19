import { useAuth } from '@/contexts/AuthContext'
import { Sun, Zap, FileText, DollarSign } from 'lucide-react'

export default function Home() {
  const { profile } = useAuth()

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-dark-900">
          Bom dia, {profile?.full_name?.split(' ')[0]}
        </h1>
        <p className="text-dark-500 mt-1">Visão geral das usinas solares</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Produção Hoje', value: '—', icon: Zap, color: 'solar' },
          { label: 'Usinas Ativas', value: '—', icon: Sun, color: 'lac' },
          { label: 'Faturas Pendentes', value: '—', icon: FileText, color: 'solar' },
          { label: 'Resultado Mensal', value: '—', icon: DollarSign, color: 'lac' },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-xl p-5 border border-dark-200 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-dark-500">{kpi.label}</span>
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                kpi.color === 'solar' ? 'bg-solar-100 text-solar-700' : 'bg-lac-100 text-lac-700'
              }`}>
                <kpi.icon size={18} />
              </div>
            </div>
            <p className="text-2xl font-bold">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-dark-200 p-8 text-center text-dark-400 shadow-sm">
        <Sun size={48} className="mx-auto mb-4 text-solar-400" />
        <p className="text-lg font-medium text-dark-600">Dashboard em construção</p>
        <p className="text-sm mt-1">Os gráficos e dados serão preenchidos nas próximas fases.</p>
      </div>
    </div>
  )
}