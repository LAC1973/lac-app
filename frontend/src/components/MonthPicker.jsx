import { ChevronLeft, ChevronRight } from 'lucide-react'
import { NOMES_MES } from '@/lib/meses'

export default function MonthPicker({ mes, ano, onPrev, onNext }) {
  return (
    <div className="flex items-center justify-center gap-4 mb-6">
      <button onClick={onPrev} className="p-2 rounded-lg hover:bg-dark-200 transition">
        <ChevronLeft size={20} />
      </button>
      <h2 className="text-lg font-semibold text-dark-900 w-48 text-center">
        {NOMES_MES[mes]} {ano}
      </h2>
      <button onClick={onNext} className="p-2 rounded-lg hover:bg-dark-200 transition">
        <ChevronRight size={20} />
      </button>
    </div>
  )
}
