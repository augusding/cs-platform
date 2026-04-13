import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

interface DemoBot {
  id: string
  name: string
  welcome_message: string
  language: string
  style: string
  avatar_url: string
  doc_count: number
  faq_count: number
}

const SUGGESTED_QUESTIONS_ZH = [
  "你们有哪些产品？",
  "价格怎么样？",
  "最小起订量是多少？",
  "支持定制吗？",
  "交货期多久？",
  "怎么付款？",
]

const SUGGESTED_QUESTIONS_EN = [
  "What products do you offer?",
  "How much does it cost?",
  "What's your MOQ?",
  "Do you support OEM?",
  "Delivery time?",
  "Payment methods?",
]

export default function Demo() {
  const navigate = useNavigate()
  const [bots, setBots] = useState<DemoBot[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/demo/bots').then(r => {
      setBots(r.data.data || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #F8FAFC 0%, #EEF2FF 50%, #F0FDFA 100%)',
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <header style={{
        padding: '16px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, background: '#185FA5',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
            </svg>
          </div>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#111827' }}>CS Platform</span>
        </div>
        <button
          onClick={() => navigate('/login')}
          style={{
            padding: '8px 20px', borderRadius: 8, fontSize: 13, fontWeight: 500,
            border: '1px solid #E5E7EB', background: '#fff', color: '#374151', cursor: 'pointer',
          }}
        >Admin login</button>
      </header>

      <section style={{
        maxWidth: 800, margin: '40px auto 0', textAlign: 'center', padding: '0 24px',
      }}>
        <div style={{
          display: 'inline-block', padding: '4px 14px', borderRadius: 20,
          background: '#EEF2FF', color: '#3730A3', fontSize: 12, fontWeight: 500, marginBottom: 16,
        }}>AI-powered customer service</div>
        <h1 style={{
          fontSize: 36, fontWeight: 700, color: '#111827', lineHeight: 1.2, marginBottom: 16,
          letterSpacing: '-0.02em',
        }}>
          Intelligent customer service<br/>that actually works
        </h1>
        <p style={{
          fontSize: 16, color: '#6B7280', lineHeight: 1.7, maxWidth: 560, margin: '0 auto 32px',
        }}>
          Upload your product docs, AI answers customer questions instantly.
          97% intent accuracy, multi-language support, lead capture built in.
          Try it live below.
        </p>
      </section>

      <section style={{ maxWidth: 900, margin: '0 auto', padding: '0 24px 40px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#9CA3AF' }}>Loading demo bots...</div>
        ) : bots.length === 0 ? (
          <div style={{
            textAlign: 'center', padding: 60, background: '#fff', borderRadius: 16,
            border: '1px solid #E5E7EB',
          }}>
            <div style={{ marginBottom: 12 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="#D1D5DB" style={{ margin: '0 auto' }}>
                <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
              </svg>
            </div>
            <p style={{ fontSize: 15, color: '#6B7280', marginBottom: 4 }}>No demo bots available yet</p>
            <p style={{ fontSize: 13, color: '#9CA3AF' }}>
              Admin: go to Bot settings and enable "Demo" to make a bot public
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: bots.length === 1 ? '1fr' : 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: 20,
          }}>
            {bots.map(bot => (
              <div key={bot.id} style={{
                background: '#fff', borderRadius: 16, border: '1px solid #E5E7EB',
                overflow: 'hidden', cursor: 'pointer',
                transition: 'box-shadow .2s, transform .2s',
              }}
                onClick={() => navigate(`/demo/${bot.id}`)}
                onMouseEnter={e => {
                  (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 30px rgba(0,0,0,.08)'
                  ;(e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={e => {
                  (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'
                  ;(e.currentTarget as HTMLDivElement).style.transform = 'none'
                }}
              >
                <div style={{ padding: '24px 24px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: 12, background: '#185FA5',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="#fff">
                      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
                    </svg>
                  </div>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: '#111827', margin: 0 }}>{bot.name}</h3>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 6,
                        background: '#EEF2FF', color: '#3730A3',
                      }}>{bot.doc_count} docs</span>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 6,
                        background: '#ECFDF5', color: '#065F46',
                      }}>{bot.faq_count} FAQ</span>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 6,
                        background: '#FFFBEB', color: '#92400E',
                      }}>{bot.language === 'zh' ? 'CN+EN' : 'EN'}</span>
                    </div>
                  </div>
                </div>

                <div style={{
                  padding: '0 24px 16px', fontSize: 13, color: '#6B7280', lineHeight: 1.5,
                }}>
                  {bot.welcome_message.slice(0, 100)}{bot.welcome_message.length > 100 ? '...' : ''}
                </div>

                <div style={{
                  padding: '12px 24px 20px', borderTop: '1px solid #F3F4F6',
                  display: 'flex', flexWrap: 'wrap', gap: 6,
                }}>
                  {(bot.language === 'zh' ? SUGGESTED_QUESTIONS_ZH : SUGGESTED_QUESTIONS_EN)
                    .slice(0, 4).map(q => (
                    <span key={q} style={{
                      fontSize: 11, padding: '4px 10px', borderRadius: 12,
                      background: '#F9FAFB', color: '#6B7280', border: '1px solid #F3F4F6',
                    }}>{q}</span>
                  ))}
                </div>

                <div style={{
                  padding: '14px 24px', background: '#F9FAFB', borderTop: '1px solid #F3F4F6',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}>
                  <span style={{ fontSize: 14, fontWeight: 500, color: '#185FA5' }}>Start live demo</span>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="#185FA5">
                    <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
                  </svg>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{
        maxWidth: 900, margin: '0 auto', padding: '0 24px 60px',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16,
        }}>
          {[
            { icon: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z',
              title: 'Agentic RAG', desc: '6-node pipeline with grading, re-retrieval, and hallucination check', color: '#EEF2FF', textColor: '#3730A3' },
            { icon: 'M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0014.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12z',
              title: 'Multi-language', desc: 'Chinese + English auto-detect, more languages coming', color: '#E1F5EE', textColor: '#085041' },
            { icon: 'M16 11c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 3-1.34 3-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z',
              title: 'Lead capture', desc: 'Auto-collect product, quantity, price, contact in natural conversation', color: '#FBEAF0', textColor: '#72243E' },
            { icon: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z',
              title: 'Easy setup', desc: 'Upload PDF/Word/Excel/URL, AI learns instantly, no training needed', color: '#FAEEDA', textColor: '#633806' },
          ].map(f => (
            <div key={f.title} style={{
              padding: '20px', borderRadius: 12, background: '#fff', border: '1px solid #F3F4F6',
            }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8, background: f.color,
                display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12,
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill={f.textColor}><path d={f.icon}/></svg>
              </div>
              <h4 style={{ fontSize: 14, fontWeight: 600, color: '#111827', marginBottom: 4 }}>{f.title}</h4>
              <p style={{ fontSize: 12, color: '#6B7280', lineHeight: 1.5, margin: 0 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer style={{
        padding: '20px 32px', borderTop: '1px solid #F3F4F6', textAlign: 'center',
        fontSize: 12, color: '#9CA3AF',
      }}>
        CS Platform · AI-powered customer service for SMEs
      </footer>
    </div>
  )
}
