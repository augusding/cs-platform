import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate, useLocation } from 'react-router-dom'
import Dashboard    from './pages/Dashboard'
import Bots         from './pages/Bots'
import BotDetail    from './pages/BotDetail'
import Knowledge    from './pages/Knowledge'
import Sessions     from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import Leads        from './pages/Leads'
import Members      from './pages/Members'
import Billing      from './pages/Billing'
import AuditLog     from './pages/AuditLog'
import Traces       from './pages/Traces'
import Profile      from './pages/Profile'
import Login        from './pages/Login'

function Icon({ d, size = 18 }: { d: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d={d} />
    </svg>
  )
}

const NAV_SECTIONS = [
  {
    label: '概览',
    items: [
      { to: '/',         label: '数据概览', icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z' },
      { to: '/sessions', label: '会话管理', icon: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z' },
    ],
  },
  {
    label: 'Bot 管理',
    items: [
      { to: '/bots',      label: 'Bot 列表', icon: 'M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2M7 14v2a5 5 0 0010 0v-2H7z' },
      { to: '/knowledge', label: '知识库',   icon: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z' },
    ],
  },
  {
    label: '运营',
    items: [
      { to: '/leads',   label: '询盘线索', icon: 'M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z' },
      { to: '/members', label: '成员管理', icon: 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z' },
      { to: '/billing', label: '套餐管理', icon: 'M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z' },
      { to: '/audit',   label: '操作审计', icon: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z' },
      { to: '/traces',  label: 'Pipeline 追踪', icon: 'M3 3v18h18v-2H5V3H3zm16 10l-4-4-4 4-4-4-1.41 1.41L9 13.59l4-4 4 4 4-4V17h2V9z' },
    ],
  },
]

const ROLE_LABEL: Record<string, string> = {
  super_admin: '超级管理员', admin: '管理员',
  operator: '客服', viewer: '观察者',
}

function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const name = localStorage.getItem('user_name') || '管理员'
  const role = localStorage.getItem('role') || ''
  const initials = name.slice(0, 1)

  const logout = () => {
    localStorage.clear()
    navigate('/login')
  }

  return (
    <aside style={{
      width: 220, flexShrink: 0, background: 'var(--sidebar-bg)',
      display: 'flex', flexDirection: 'column', height: '100vh',
      position: 'sticky', top: 0,
    }}>
      <div style={{ padding: '22px 20px 18px', borderBottom: '1px solid var(--sidebar-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, background: '#3B82F6', borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="#fff">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', lineHeight: 1.2 }}>CS Platform</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,.35)', marginTop: 1 }}>智能客服系统</div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '14px 10px', overflowY: 'auto' }}>
        {NAV_SECTIONS.map(section => (
          <div key={section.label} style={{ marginBottom: 22 }}>
            <div style={{
              fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,.28)',
              letterSpacing: '.08em', textTransform: 'uppercase',
              padding: '0 10px', marginBottom: 4,
            }}>{section.label}</div>
            {section.items.map(item => {
              const isActive = item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to)
              return (
                <NavLink key={item.to} to={item.to} style={{ textDecoration: 'none' }}>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 9,
                    padding: '8px 10px', borderRadius: 8, marginBottom: 1,
                    background: isActive ? 'rgba(59,130,246,.2)' : 'transparent',
                    cursor: 'pointer', transition: 'background .1s',
                  }}
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,.06)' }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLDivElement).style.background = 'transparent' }}
                  >
                    <span style={{ color: isActive ? '#93C5FD' : 'rgba(255,255,255,.4)', flexShrink: 0 }}>
                      <Icon d={item.icon} />
                    </span>
                    <span style={{
                      fontSize: 13, color: isActive ? '#fff' : 'rgba(255,255,255,.6)',
                      fontWeight: isActive ? 500 : 400, flex: 1,
                    }}>{item.label}</span>
                  </div>
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      <div style={{ padding: '12px 10px', borderTop: '1px solid var(--sidebar-border)' }}>
        <NavLink to="/profile" style={{ textDecoration: 'none' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
          }}
            onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,.06)'}
            onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.background = 'transparent'}
          >
            <div style={{
              width: 30, height: 30, borderRadius: '50%',
              background: '#3B82F6', display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: 13, fontWeight: 600,
              color: '#fff', flexShrink: 0,
            }}>{initials}</div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,.85)', fontWeight: 500 }}>{name}</div>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,.35)' }}>{ROLE_LABEL[role] || role}</div>
            </div>
          </div>
        </NavLink>
        <button onClick={logout} style={{
          width: '100%', marginTop: 4, padding: '6px 10px',
          background: 'transparent', border: 'none', cursor: 'pointer',
          fontSize: 12, color: 'rgba(255,255,255,.3)', textAlign: 'left',
          borderRadius: 6,
        }}
          onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,.6)'}
          onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,.3)'}
        >退出登录</button>
      </div>
    </aside>
  )
}

function Layout({ children, title, action }: {
  children: React.ReactNode
  title: string
  action?: React.ReactNode
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh', overflow: 'hidden' }}>
      <header style={{
        height: 56, background: '#fff', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 28px', flexShrink: 0, position: 'sticky', top: 0, zIndex: 10,
      }}>
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{title}</h1>
        {action && <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>{action}</div>}
      </header>
      <main style={{ flex: 1, padding: 28, overflowY: 'auto' }}>
        {children}
      </main>
    </div>
  )
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('access_token')
    ? <>{children}</>
    : <Navigate to="/login" replace />
}

function Shell() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar />
      <Routes>
        <Route path="/" element={<Layout title="数据概览"><Dashboard /></Layout>} />
        <Route path="/bots" element={<Layout title="Bot 列表"><Bots /></Layout>} />
        <Route path="/bots/:botId" element={<Layout title="Bot 配置"><BotDetail /></Layout>} />
        <Route path="/knowledge" element={<Layout title="知识库管理"><Knowledge /></Layout>} />
        <Route path="/sessions" element={<Layout title="会话管理"><Sessions /></Layout>} />
        <Route path="/sessions/:sessionId" element={<Layout title="会话详情"><SessionDetail /></Layout>} />
        <Route path="/leads" element={<Layout title="询盘线索"><Leads /></Layout>} />
        <Route path="/members" element={<Layout title="成员管理"><Members /></Layout>} />
        <Route path="/billing" element={<Layout title="套餐管理"><Billing /></Layout>} />
        <Route path="/audit" element={<Layout title="操作审计"><AuditLog /></Layout>} />
        <Route path="/traces" element={<Layout title="Pipeline 追踪"><Traces /></Layout>} />
        <Route path="/profile" element={<Layout title="个人设置"><Profile /></Layout>} />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/*" element={<PrivateRoute><Shell /></PrivateRoute>} />
      </Routes>
    </BrowserRouter>
  )
}
