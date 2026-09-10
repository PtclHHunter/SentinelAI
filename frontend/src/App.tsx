import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { useState, createContext, useContext, useCallback } from 'react'
import { LayoutDashboard, FileText, Search, Hash, FolderOpen, FileBarChart, Shield, Menu, X, Bell } from 'lucide-react'
import DashboardPage from './pages/Dashboard'
import LogAnalyzerPage from './pages/LogAnalyzer'
import IOCScannerPage from './pages/IOCScanner'
import HashAnalyzerPage from './pages/HashAnalyzer'
import InvestigationsPage from './pages/Investigations'
import ReportsPage from './pages/Reports'

// Toast context
interface Toast { id: number; message: string; type: 'success' | 'error' | 'info' }
const ToastContext = createContext<{ toast: (msg: string, type?: Toast['type']) => void }>({ toast: () => {} })
export const useToast = () => useContext(ToastContext)

function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const toast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])
  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map(t => (
          <div key={t.id} className={`toast-enter px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            t.type === 'success' ? 'bg-sentinel-low text-white' :
            t.type === 'error' ? 'bg-sentinel-critical text-white' :
            'bg-sentinel-card border border-sentinel-border text-sentinel-text'
          }`}>{t.message}</div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
  { to: '/logs', icon: FileText, label: 'Log Analyzer' },
  { to: '/ioc', icon: Search, label: 'IOC Scanner' },
  { to: '/hash', icon: Hash, label: 'Hash Analyzer' },
  { to: '/investigations', icon: FolderOpen, label: 'Investigations' },
  { to: '/reports', icon: FileBarChart, label: 'Reports' },
]

function NavRail({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <nav className={`fixed left-0 top-0 h-full bg-sentinel-card border-r border-sentinel-border z-40 transition-all duration-200 ${
      collapsed ? 'w-16' : 'w-56'
    }`}>
      <div className="flex items-center gap-2 px-4 h-14 border-b border-sentinel-border">
        <Shield className="w-6 h-6 text-sentinel-cyan flex-shrink-0" />
        {!collapsed && <span className="text-lg font-bold text-sentinel-cyan">SentinelAI</span>}
        <button onClick={onToggle} className="ml-auto p-1 hover:bg-sentinel-border rounded text-sentinel-text-secondary">
          {collapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
        </button>
      </div>
      <div className="py-2">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-colors ${
                isActive ? 'bg-sentinel-cyan/10 text-sentinel-cyan border-l-2 border-sentinel-cyan' : 'text-sentinel-text-secondary hover:bg-sentinel-border hover:text-sentinel-text'
              } ${collapsed ? 'justify-center px-2' : ''}`
            }
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

export default function App() {
  const [navCollapsed, setNavCollapsed] = useState(false)
  return (
    <BrowserRouter>
      <ToastProvider>
        <div className="min-h-screen bg-sentinel-bg text-sentinel-text">
          <NavRail collapsed={navCollapsed} onToggle={() => setNavCollapsed(!navCollapsed)} />
          <main className={`transition-all duration-200 ${navCollapsed ? 'ml-16' : 'ml-56'}`}>
            <header className="sticky top-0 z-30 bg-sentinel-bg/80 backdrop-blur border-b border-sentinel-border h-14 flex items-center px-6">
              <h1 className="text-sm text-sentinel-text-secondary">Cybersecurity Analysis Platform</h1>
              <div className="ml-auto flex items-center gap-3">
                <div className="relative">
                  <Bell className="w-5 h-5 text-sentinel-text-secondary" />
                  <span className="absolute -top-1 -right-1 w-2 h-2 bg-sentinel-critical rounded-full"></span>
                </div>
                <span className="text-xs text-sentinel-text-secondary">Local Mode</span>
              </div>
            </header>
            <div className="p-6">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/logs" element={<LogAnalyzerPage />} />
                <Route path="/ioc" element={<IOCScannerPage />} />
                <Route path="/hash" element={<HashAnalyzerPage />} />
                <Route path="/investigations" element={<InvestigationsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Routes>
            </div>
          </main>
        </div>
      </ToastProvider>
    </BrowserRouter>
  )
}