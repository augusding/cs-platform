import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Bots from './pages/Bots'
import BotDetail from './pages/BotDetail'
import Knowledge from './pages/Knowledge'
import Sessions from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import Leads from './pages/Leads'
import Billing from './pages/Billing'
import Members from './pages/Members'
import AuditLog from './pages/AuditLog'
import Profile from './pages/Profile'
import Login from './pages/Login'

function Layout({ children }: { children: React.ReactNode }) {
  const nav = [
    { to: '/', label: '数据概览' },
    { to: '/bots', label: 'Bot 管理' },
    { to: '/knowledge', label: '知识库' },
    { to: '/sessions', label: '会话记录' },
    { to: '/leads', label: '询盘线索' },
    { to: '/members', label: '成员管理' },
    { to: '/audit', label: '操作审计' },
    { to: '/billing', label: '套餐管理' },
  ]
  const logout = () => {
    localStorage.removeItem('access_token')
    window.location.href = '/login'
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-52 bg-white border-r border-gray-100 flex flex-col">
        <div className="p-5 border-b border-gray-100">
          <p className="font-semibold text-gray-800">CS Platform</p>
          <p className="text-xs text-gray-400 mt-0.5">Admin Console</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-100 p-3 space-y-1">
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              `block px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-blue-50 text-blue-600 font-medium'
                  : 'text-gray-500 hover:bg-gray-50'
              }`
            }
          >
            个人设置
          </NavLink>
          <button
            onClick={logout}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-400 hover:bg-gray-50 hover:text-gray-600"
          >
            退出登录
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  )
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('access_token') ? (
    <>{children}</>
  ) : (
    <Navigate to="/login" replace />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/bots" element={<Bots />} />
                  <Route path="/bots/:botId" element={<BotDetail />} />
                  <Route path="/knowledge" element={<Knowledge />} />
                  <Route path="/sessions" element={<Sessions />} />
                  <Route path="/sessions/:sessionId" element={<SessionDetail />} />
                  <Route path="/leads" element={<Leads />} />
                  <Route path="/billing" element={<Billing />} />
                  <Route path="/members" element={<Members />} />
                  <Route path="/audit" element={<AuditLog />} />
                  <Route path="/profile" element={<Profile />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
