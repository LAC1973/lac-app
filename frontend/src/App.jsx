import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import DashboardLayout from '@/components/layout/DashboardLayout'
import ProtectedRoute from '@/components/ProtectedRoute'
import Login from '@/pages/Login'
import Home from '@/pages/Home'
import Funcionarios from '@/pages/Funcionarios'
import SemAcesso from '@/pages/SemAcesso'
import Usinas from '@/pages/Usinas'
import Clientes from '@/pages/Clientes'
import Producao from '@/pages/Producao'
import Faturas from '@/pages/Faturas'
import Recibos from '@/pages/Recibos'
import Percentuais from '@/pages/Percentuais'
import RGD from '@/pages/RGD'
import SaldoACM from '@/pages/SaldoACM'
import DRE from '@/pages/DRE'
import Despesas from '@/pages/Despesas'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/sem-acesso" element={<SemAcesso />} />

          <Route element={<DashboardLayout />}>
            <Route path="/" element={
              <ProtectedRoute modulo="dashboard"><Home /></ProtectedRoute>
            } />
           <Route path="/funcionarios" element={<Funcionarios />} />
          <Route path="/usinas" element={
            <ProtectedRoute modulo="usinas"><Usinas /></ProtectedRoute>
          } />
          <Route path="/clientes" element={
            <ProtectedRoute modulo="clientes"><Clientes /></ProtectedRoute>
          } />
          <Route path="/producao" element={
            <ProtectedRoute modulo="producao"><Producao /></ProtectedRoute>
          } />
          <Route path="/faturas" element={
            <ProtectedRoute modulo="faturas"><Faturas /></ProtectedRoute>
          } />
          <Route path="/recibos" element={
            <ProtectedRoute modulo="recibos"><Recibos /></ProtectedRoute>
          } />
          <Route path="/percentuais" element={
            <ProtectedRoute modulo="percentuais"><Percentuais /></ProtectedRoute>
          } />
          <Route path="/rgd" element={
            <ProtectedRoute modulo="rgd"><RGD /></ProtectedRoute>
          } />
          <Route path="/saldo-acm" element={
            <ProtectedRoute modulo="saldo_acm"><SaldoACM /></ProtectedRoute>
          } />
          <Route path="/dre" element={
            <ProtectedRoute modulo="dre"><DRE /></ProtectedRoute>
          } />
          <Route path="/despesas" element={
            <ProtectedRoute modulo="despesas"><Despesas /></ProtectedRoute>
          } />

            {[
              { path: '/usinas', modulo: 'usinas', title: 'Usinas' },
              { path: '/usinas', modulo: 'usinas', title: 'Usinas' },
            ].map((r) => (
              <Route key={r.path} path={r.path} element={
                <ProtectedRoute modulo={r.modulo}>
                  <div className="bg-white rounded-xl border border-dark-200 p-12 text-center shadow-sm">
                    <h1 className="text-xl font-bold text-dark-700 mb-2">{r.title}</h1>
                    <p className="text-dark-400">Em breve</p>
                  </div>
                </ProtectedRoute>
              } />
            ))}
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}