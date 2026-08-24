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
import Configuracoes from '@/pages/Configuracoes'

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
            <Route path="/configuracoes" element={<Configuracoes />} />
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
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}