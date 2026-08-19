import { ShieldX } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function SemAcesso() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <ShieldX size={64} className="text-dark-300 mb-4" />
      <h1 className="text-xl font-bold text-dark-700 mb-2">Sem Acesso</h1>
      <p className="text-dark-500 mb-6">Você não tem permissão para acessar esta página.</p>
      <Link
        to="/"
        className="px-6 py-2.5 rounded-lg bg-solar-500 hover:bg-solar-600 text-dark-900 font-semibold text-sm transition"
      >
        Voltar ao início
      </Link>
    </div>
  )
}