import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

interface BotInfo {
  id: string; name: string; welcome_message: string
  language: string; bot_api_key: string
}

interface ChatMsg {
  id: string; role: 'user' | 'bot' | 'system'
  content: string; time: string
}

const QUICK_REPLIES_ZH = [
  "你们有哪些产品？", "价格怎么样？", "最小起订量？",
  "支持定制吗？", "交货期多久？", "怎么付款？",
]
const QUICK_REPLIES_EN = [
  "What products do you offer?", "Pricing?", "MOQ?",
  "OEM available?", "Delivery time?", "Payment methods?",
]

function now() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
}

let _msgId = 0
function msgId() { return `m_${++_msgId}` }

export default function DemoChat() {
  const { botId } = useParams<{ botId: string }>()
  const navigate = useNavigate()

  const [bot, setBot] = useState<BotInfo | null>(null)
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')

  const wsRef = useRef<WebSocket | null>(null)
  const msgsRef = useRef<HTMLDivElement>(null)
  const tokenBuf = useRef('')

  useEffect(() => {
    if (!botId) return
    api.get(`/demo/bots/${botId}`).then(r => {
      setBot(r.data.data)
    }).catch(() => {
      setError('Demo bot not found')
    })
  }, [botId])

  useEffect(() => {
    if (!bot || !bot.bot_api_key) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.hostname
    const port = window.location.port === '3001' ? '8081' : window.location.port
    const visitor = 'demo_' + Math.random().toString(36).slice(2)

    const ws = new WebSocket(
      `${proto}://${host}:${port}/api/chat/${bot.id}?key=${bot.bot_api_key}&visitor_id=${visitor}`
    )
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'connected') {
        setMessages([{
          id: msgId(), role: 'bot',
          content: msg.welcome || bot.welcome_message || 'Hello!',
          time: now(),
        }])
      } else if (msg.type === 'token') {
        tokenBuf.current += msg.content
        setMessages(prev => {
          const copy = [...prev]
          const last = copy[copy.length - 1]
          if (last?.role === 'bot') {
            copy[copy.length - 1] = { ...last, content: tokenBuf.current }
          }
          return copy
        })
        requestAnimationFrame(() => {
          msgsRef.current?.scrollTo(0, msgsRef.current.scrollHeight)
        })
      } else if (msg.type === 'done') {
        tokenBuf.current = ''
        setSending(false)
      } else if (msg.type === 'error') {
        tokenBuf.current = ''
        setSending(false)
        setMessages(prev => [
          ...prev.filter(m => m.content !== '...'),
          { id: msgId(), role: 'system', content: 'Sorry, please try again.', time: now() },
        ])
      } else if (msg.type === 'transfer') {
        setMessages(prev => [
          ...prev,
          { id: msgId(), role: 'system', content: msg.message || 'Transferring to human agent...', time: now() },
        ])
      } else if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
      }
    }

    ws.onclose = () => setConnected(false)
    ws.onerror = () => setConnected(false)

    return () => ws.close()
  }, [bot])

  useEffect(() => {
    msgsRef.current?.scrollTo(0, msgsRef.current.scrollHeight)
  }, [messages])

  const send = (text?: string) => {
    const content = (text || input).trim()
    if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || sending) return

    setSending(true)
    tokenBuf.current = ''
    setMessages(prev => [
      ...prev,
      { id: msgId(), role: 'user', content, time: now() },
      { id: msgId(), role: 'bot', content: '...', time: now() },
    ])
    setInput('')
    wsRef.current.send(JSON.stringify({ type: 'message', content }))
  }

  const quickReplies = bot?.language === 'en' ? QUICK_REPLIES_EN : QUICK_REPLIES_ZH
  const showQuickReplies = !messages.some(m => m.role === 'user')

  if (error) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', -apple-system, sans-serif", color: '#6B7280',
      }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 16, marginBottom: 12 }}>{error}</p>
          <button onClick={() => navigate('/demo')} style={{
            padding: '8px 20px', borderRadius: 8, background: '#185FA5', color: '#fff',
            border: 'none', cursor: 'pointer', fontSize: 14,
          }}>Back to demo list</button>
        </div>
      </div>
    )
  }

  if (!bot) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'Inter', -apple-system, sans-serif", color: '#9CA3AF',
      }}>Loading...</div>
    )
  }

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      fontFamily: "'Inter', -apple-system, sans-serif",
      background: '#F8FAFC',
    }}>
      <header style={{
        padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 12,
        background: '#fff', borderBottom: '1px solid #E5E7EB', flexShrink: 0,
      }}>
        <button onClick={() => navigate('/demo')} style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: 4,
          color: '#9CA3AF', display: 'flex', alignItems: 'center',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
        </button>
        <div style={{
          width: 36, height: 36, borderRadius: 10, background: '#185FA5',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
          </svg>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ fontSize: 15, fontWeight: 600, color: '#111827', margin: 0 }}>{bot.name}</h1>
          <p style={{
            fontSize: 11, margin: 0, display: 'flex', alignItems: 'center', gap: 4,
            color: connected ? '#059669' : '#9CA3AF',
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: 3,
              background: connected ? '#10B981' : '#D1D5DB',
              display: 'inline-block',
            }}/>
            {connected ? 'Online' : 'Connecting...'}
          </p>
        </div>
        <span style={{ fontSize: 11, color: '#C4C4C4' }}>Powered by CS Platform</span>
      </header>

      <div ref={msgsRef} style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {messages.map(m => (
          <div key={m.id} style={{
            display: 'flex',
            flexDirection: m.role === 'user' ? 'row-reverse' : 'row',
            gap: 8, alignItems: 'flex-end',
          }}>
            {m.role === 'bot' && (
              <div style={{
                width: 28, height: 28, borderRadius: 8, background: '#185FA5',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="#fff">
                  <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
                </svg>
              </div>
            )}
            <div style={{ maxWidth: '75%' }}>
              <div style={{
                padding: '10px 14px',
                borderRadius: m.role === 'user' ? '16px 4px 16px 16px'
                  : m.role === 'system' ? '8px' : '4px 16px 16px 16px',
                background: m.role === 'user' ? '#185FA5'
                  : m.role === 'system' ? '#FEF3C7' : '#fff',
                color: m.role === 'user' ? '#fff'
                  : m.role === 'system' ? '#92400E' : '#111827',
                fontSize: 14, lineHeight: 1.6, wordBreak: 'break-word',
                border: m.role === 'bot' ? '1px solid #E5E7EB' : 'none',
                whiteSpace: 'pre-wrap',
              }}>
                {m.content === '...' ? (
                  <span style={{ display: 'inline-flex', gap: 4, padding: '2px 0' }}>
                    {[0, 1, 2].map(i => (
                      <span key={i} style={{
                        width: 6, height: 6, borderRadius: 3, background: '#C4C4C4',
                        display: 'inline-block',
                        animation: `typing-dot 1.4s infinite ${i * 0.2}s`,
                      }}/>
                    ))}
                    <style>{`@keyframes typing-dot { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }`}</style>
                  </span>
                ) : m.content}
              </div>
              <div style={{
                fontSize: 10, color: '#C4C4C4', marginTop: 4,
                textAlign: m.role === 'user' ? 'right' : 'left',
              }}>{m.time}</div>
            </div>
          </div>
        ))}
      </div>

      {showQuickReplies && (
        <div style={{
          padding: '0 20px 8px', display: 'flex', flexWrap: 'wrap', gap: 6,
        }}>
          {quickReplies.map(q => (
            <button key={q} onClick={() => send(q)} style={{
              fontSize: 12, padding: '6px 14px', borderRadius: 16,
              border: '1px solid #E5E7EB', background: '#fff', color: '#374151',
              cursor: 'pointer', transition: 'background .15s',
            }}
              onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.background = '#F3F4F6'}
              onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.background = '#fff'}
            >{q}</button>
          ))}
        </div>
      )}

      <div style={{
        padding: '12px 20px', background: '#fff', borderTop: '1px solid #E5E7EB',
        display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0,
      }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder={bot.language === 'zh' ? '输入您的问题...' : 'Type your message...'}
          disabled={sending || !connected}
          style={{
            flex: 1, border: '1px solid #E5E7EB', borderRadius: 24,
            padding: '10px 18px', fontSize: 14, outline: 'none',
            background: '#F9FAFB', color: '#111827',
            transition: 'border-color .15s',
          }}
          onFocus={e => e.currentTarget.style.borderColor = '#185FA5'}
          onBlur={e => e.currentTarget.style.borderColor = '#E5E7EB'}
        />
        <button onClick={() => send()} disabled={sending || !input.trim() || !connected} style={{
          width: 40, height: 40, borderRadius: 20, border: 'none',
          background: sending || !input.trim() ? '#E5E7EB' : '#185FA5',
          cursor: sending || !input.trim() ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background .15s', flexShrink: 0,
        }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>

      <div style={{
        padding: '8px 20px', background: '#fff', borderTop: '1px solid #F3F4F6',
        display: 'flex', justifyContent: 'center', gap: 16,
        fontSize: 11, color: '#C4C4C4', flexShrink: 0,
      }}>
        <span>AI-powered</span>
        <span style={{ color: '#E5E7EB' }}>|</span>
        <span>24/7 available</span>
        <span style={{ color: '#E5E7EB' }}>|</span>
        <span>Secure & private</span>
      </div>
    </div>
  )
}
