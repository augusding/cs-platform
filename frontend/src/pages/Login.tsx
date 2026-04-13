import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../api/client'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const isRegister = location.pathname === '/register'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [company, setCompany] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    setError('')
    if (isRegister && password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      if (isRegister) {
        await api.post('/auth/register', {
          email,
          password,
          name: name || email.split('@')[0],
          company_name: company || 'My Company',
        })
      }
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('access_token', data.data.access_token)
      localStorage.setItem('role', data.data.role)
      try {
        const me = await api.get('/auth/me')
        if (me.data?.data?.name) localStorage.setItem('user_name', me.data.data.name)
      } catch {}
      window.location.href = '/'
    } catch (e: any) {
      setError(
        e.response?.data?.reason ||
        e.userMessage ||
        (isRegister ? 'Registration failed' : 'Login failed')
      )
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '10px 14px', borderRadius: 10,
    border: '1px solid #E2E8F0', fontSize: 14, marginBottom: 16,
    outline: 'none', transition: 'border-color .15s',
    color: '#0F172A', background: '#fff',
  }
  const focusOn = (e: React.FocusEvent<HTMLInputElement>) =>
    (e.currentTarget.style.borderColor = '#2563EB')
  const focusOff = (e: React.FocusEvent<HTMLInputElement>) =>
    (e.currentTarget.style.borderColor = '#E2E8F0')

  return (
    <div style={{
      minHeight: '100vh', display: 'flex',
      fontFamily: "'Inter', -apple-system, 'Segoe UI', sans-serif",
    }}>
      {/* Left: Brand panel */}
      <div style={{
        flex: 1, background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '60px 48px', position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.03,
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}/>

        <div style={{ position: 'relative', maxWidth: 400 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 40, cursor: 'pointer' }}
            onClick={() => navigate('/home')}>
            <div style={{
              width: 36, height: 36, borderRadius: 10, background: '#2563EB',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            <span style={{ fontSize: 18, fontWeight: 600, color: '#fff' }}>CS Platform</span>
          </div>

          <h2 style={{
            fontSize: 28, fontWeight: 700, color: '#fff', lineHeight: 1.3,
            marginBottom: 16, letterSpacing: '-0.02em',
          }}>
            AI customer service<br/>that never sleeps
          </h2>
          <p style={{ fontSize: 14, color: '#94A3B8', lineHeight: 1.7, marginBottom: 32 }}>
            Upload your product docs and let AI handle customer inquiries 24/7.
            97% accuracy. Zero hallucinations. Captures leads automatically.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              'Agentic RAG with self-correction',
              '5-layer intent recognition (23 intents)',
              'Smart lead capture in natural conversation',
              'Full pipeline observability',
            ].map(f => (
              <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#2563EB">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                <span style={{ fontSize: 13, color: '#CBD5E1' }}>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right: Form */}
      <div style={{
        width: 480, display: 'flex', flexDirection: 'column',
        justifyContent: 'center', padding: '60px 48px', background: '#fff',
      }}>
        <h1 style={{
          fontSize: 24, fontWeight: 700, color: '#0F172A', marginBottom: 6,
          letterSpacing: '-0.02em',
        }}>
          {isRegister ? 'Create your account' : 'Welcome back'}
        </h1>
        <p style={{ fontSize: 14, color: '#94A3B8', marginBottom: 28 }}>
          {isRegister
            ? 'Start your free account — no credit card required'
            : 'Enter your credentials to access the console'
          }
        </p>

        {error && (
          <div style={{
            padding: '10px 14px', borderRadius: 10, marginBottom: 16,
            background: '#FEF2F2', color: '#DC2626', fontSize: 13,
            border: '1px solid #FECACA',
          }}>{error}</div>
        )}

        {isRegister && (
          <>
            <label style={{ fontSize: 13, fontWeight: 500, color: '#334155', marginBottom: 6, display: 'block' }}>
              Your name
            </label>
            <input
              value={name} onChange={e => setName(e.target.value)}
              placeholder="John Doe"
              style={inputStyle} onFocus={focusOn} onBlur={focusOff}
            />

            <label style={{ fontSize: 13, fontWeight: 500, color: '#334155', marginBottom: 6, display: 'block' }}>
              Company name
            </label>
            <input
              value={company} onChange={e => setCompany(e.target.value)}
              placeholder="Acme Electronics"
              style={inputStyle} onFocus={focusOn} onBlur={focusOff}
            />
          </>
        )}

        <label style={{ fontSize: 13, fontWeight: 500, color: '#334155', marginBottom: 6, display: 'block' }}>
          Email
        </label>
        <input
          type="email" value={email} onChange={e => setEmail(e.target.value)}
          placeholder="you@company.com"
          style={inputStyle} onFocus={focusOn} onBlur={focusOff}
        />

        <label style={{ fontSize: 13, fontWeight: 500, color: '#334155', marginBottom: 6, display: 'block' }}>
          Password {isRegister && <span style={{ color: '#94A3B8', fontWeight: 400 }}>(min 8 chars)</span>}
        </label>
        <input
          type="password" value={password} onChange={e => setPassword(e.target.value)}
          placeholder="••••••••"
          onKeyDown={e => e.key === 'Enter' && submit()}
          style={{ ...inputStyle, marginBottom: 24 }} onFocus={focusOn} onBlur={focusOff}
        />

        <button
          onClick={submit} disabled={loading}
          style={{
            width: '100%', padding: '12px', borderRadius: 10, border: 'none',
            background: '#2563EB', color: '#fff', fontSize: 15, fontWeight: 500,
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading ? 0.7 : 1, transition: 'opacity .15s, transform .1s',
          }}
          onMouseDown={e => { if (!loading) (e.currentTarget as HTMLButtonElement).style.transform = 'scale(0.98)' }}
          onMouseUp={e => (e.currentTarget as HTMLButtonElement).style.transform = 'none'}
        >
          {loading
            ? (isRegister ? 'Creating account...' : 'Signing in...')
            : (isRegister ? 'Create account' : 'Sign in')
          }
        </button>

        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: '#94A3B8' }}>
          {isRegister ? 'Already have an account? ' : "Don't have an account? "}
          <span
            onClick={() => navigate(isRegister ? '/login' : '/register')}
            style={{ color: '#2563EB', cursor: 'pointer', fontWeight: 500 }}
          >
            {isRegister ? 'Sign in' : 'Create one'}
          </span>
        </p>

        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <span
            onClick={() => navigate('/demo')}
            style={{ fontSize: 13, color: '#94A3B8', cursor: 'pointer', textDecoration: 'underline' }}
          >
            or try the live demo first
          </span>
        </div>
      </div>
    </div>
  )
}
