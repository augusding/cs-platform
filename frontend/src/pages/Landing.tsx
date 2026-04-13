import { useNavigate } from 'react-router-dom'
import { useEffect, useRef } from 'react'

const S = {
  page: { fontFamily: "'Inter', -apple-system, 'Segoe UI', sans-serif", color: '#0F172A', overflowX: 'hidden' as const },
  nav: { position: 'fixed' as const, top: 0, left: 0, right: 0, zIndex: 50, padding: '14px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', transition: 'background .3s, box-shadow .3s' },
  logo: { display: 'flex', alignItems: 'center', gap: 10 },
  logoIcon: { width: 32, height: 32, borderRadius: 8, background: '#2563EB', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  navLinks: { display: 'flex', gap: 28, fontSize: 14, color: 'rgba(255,255,255,.7)' },
  navLink: { textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'color .2s' },
  btnPrimary: { padding: '10px 24px', borderRadius: 12, background: '#2563EB', color: '#fff', border: 'none', fontSize: 14, fontWeight: 500 as const, cursor: 'pointer', transition: 'transform .15s, box-shadow .15s' },
  btnOutline: { padding: '10px 24px', borderRadius: 12, background: 'transparent', color: '#fff', border: '1px solid rgba(255,255,255,.25)', fontSize: 14, fontWeight: 500 as const, cursor: 'pointer', transition: 'background .15s' },
}

function FeatureCard({ icon, title, desc, accent }: { icon: string; title: string; desc: string; accent: string }) {
  return (
    <div style={{
      background: '#fff', borderRadius: 16, padding: '28px 24px',
      border: '1px solid #F1F5F9', transition: 'transform .2s, box-shadow .2s',
      cursor: 'default',
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = '0 12px 40px rgba(0,0,0,.06)' }}
      onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none' }}
    >
      <div style={{
        width: 44, height: 44, borderRadius: 12, background: accent + '15',
        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16,
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill={accent}><path d={icon}/></svg>
      </div>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#0F172A' }}>{title}</h3>
      <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.7, margin: 0 }}>{desc}</p>
    </div>
  )
}

function StatCard({ num, label }: { num: string; label: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 36, fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>{num}</div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,.6)', marginTop: 4 }}>{label}</div>
    </div>
  )
}

function StepCard({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '0 12px' }}>
      <div style={{
        width: 48, height: 48, borderRadius: 24, background: '#2563EB',
        color: '#fff', fontSize: 18, fontWeight: 600,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 16px',
      }}>{num}</div>
      <h4 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6, color: '#0F172A' }}>{title}</h4>
      <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, margin: 0 }}>{desc}</p>
    </div>
  )
}

function CompareRow({ feature, us, them }: { feature: string; us: string; them: string }) {
  return (
    <tr style={{ borderBottom: '1px solid #F1F5F9' }}>
      <td style={{ padding: '14px 16px', fontSize: 14, color: '#334155', fontWeight: 500 }}>{feature}</td>
      <td style={{ padding: '14px 16px', fontSize: 13, color: '#2563EB', fontWeight: 500, textAlign: 'center' }}>{us}</td>
      <td style={{ padding: '14px 16px', fontSize: 13, color: '#94A3B8', textAlign: 'center' }}>{them}</td>
    </tr>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const navRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const handleScroll = () => {
      if (navRef.current) {
        const scrolled = window.scrollY > 60
        navRef.current.style.background = scrolled ? 'rgba(15,23,42,.95)' : 'transparent'
        navRef.current.style.boxShadow = scrolled ? '0 1px 20px rgba(0,0,0,.1)' : 'none'
        navRef.current.style.backdropFilter = scrolled ? 'blur(12px)' : 'none'
      }
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div style={S.page}>
      <nav ref={navRef} style={S.nav}>
        <div style={S.logo}>
          <div style={S.logoIcon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#fff"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
          </div>
          <span style={{ fontSize: 16, fontWeight: 600, color: '#fff' }}>CS Platform</span>
        </div>
        <div style={S.navLinks}>
          <a href="#features" style={S.navLink}>Features</a>
          <a href="#how" style={S.navLink}>How it works</a>
          <a href="#compare" style={S.navLink}>Compare</a>
          <a href="#pricing" style={S.navLink}>Pricing</a>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button style={S.btnOutline} onClick={() => navigate('/login')}>Log in</button>
          <button style={S.btnPrimary} onClick={() => navigate('/demo')}>Live demo</button>
        </div>
      </nav>

      {/* Hero */}
      <section style={{
        background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0F172A 100%)',
        padding: '140px 32px 80px', textAlign: 'center', position: 'relative', overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.04,
          backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}/>

        <div style={{ position: 'relative', maxWidth: 760, margin: '0 auto' }}>
          <div style={{
            display: 'inline-block', padding: '6px 16px', borderRadius: 20,
            background: 'rgba(37,99,235,.15)', color: '#60A5FA',
            fontSize: 13, fontWeight: 500, marginBottom: 24, border: '1px solid rgba(37,99,235,.2)',
          }}>
            AI-native customer service for SMEs
          </div>

          <h1 style={{
            fontSize: 48, fontWeight: 700, color: '#fff', lineHeight: 1.15,
            letterSpacing: '-0.03em', marginBottom: 20,
          }}>
            Your smartest employee<br/>never sleeps
          </h1>

          <p style={{
            fontSize: 18, color: '#94A3B8', lineHeight: 1.7,
            maxWidth: 540, margin: '0 auto 36px',
          }}>
            Upload your product docs. Get an AI agent that answers customers 24/7
            with 97% accuracy — in Chinese, English, or both.
            Captures leads. Never hallucinates.
          </p>

          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', marginBottom: 60 }}>
            <button style={{ ...S.btnPrimary, padding: '14px 32px', fontSize: 16 }}
              onClick={() => navigate('/demo')}
              onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.03)'; e.currentTarget.style.boxShadow = '0 8px 30px rgba(37,99,235,.3)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none' }}
            >Try live demo</button>
            <button style={{ ...S.btnOutline, padding: '14px 32px', fontSize: 16 }}
              onClick={() => navigate('/register')}
              onMouseEnter={e => (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,.08)'}
              onMouseLeave={e => (e.currentTarget as HTMLButtonElement).style.background = 'transparent'}
            >Start free</button>
          </div>

          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20,
            maxWidth: 600, margin: '0 auto',
            padding: '24px 0', borderTop: '1px solid rgba(255,255,255,.08)',
          }}>
            <StatCard num="97%" label="Intent accuracy" />
            <StatCard num="6s" label="Avg response" />
            <StatCard num="24/7" label="Always on" />
            <StatCard num="0" label="Hallucinations" />
          </div>
        </div>
      </section>

      {/* Pain Points */}
      <section style={{ padding: '80px 32px', background: '#fff' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 12, letterSpacing: '-0.02em' }}>
            Your customers have questions.<br/>Your team is busy.
          </h2>
          <p style={{ fontSize: 16, color: '#64748B', lineHeight: 1.7, maxWidth: 560, margin: '0 auto 48px' }}>
            80% of customer questions are repetitive. Product specs, pricing, MOQ, shipping —
            the same questions, over and over. Let AI handle them instantly while your team
            focuses on deals that actually need a human.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
            {[
              { num: '80%', label: 'of inquiries are repetitive questions your docs already answer', color: '#2563EB' },
              { num: '5min', label: 'average wait time frustrates customers — AI responds in seconds', color: '#059669' },
              { num: '40%', label: 'of leads are lost when no one responds outside business hours', color: '#DC2626' },
            ].map(s => (
              <div key={s.label} style={{
                padding: '32px 24px', borderRadius: 16, background: '#F8FAFC',
                border: '1px solid #F1F5F9',
              }}>
                <div style={{ fontSize: 40, fontWeight: 700, color: s.color, marginBottom: 8 }}>{s.num}</div>
                <p style={{ fontSize: 13, color: '#64748B', lineHeight: 1.6, margin: 0 }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ padding: '80px 32px', background: '#F8FAFC' }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{
              display: 'inline-block', padding: '4px 14px', borderRadius: 8,
              background: '#EEF2FF', color: '#3730A3', fontSize: 12, fontWeight: 600,
              letterSpacing: '.05em', textTransform: 'uppercase' as const, marginBottom: 12,
            }}>Features</div>
            <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em' }}>
              Not just a chatbot. An AI agent.
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            <FeatureCard
              icon="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7H3a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2M7 14v2a5 5 0 0010 0v-2H7z"
              title="Agentic RAG pipeline"
              desc="6-node pipeline: Router → QueryTransform → Retriever → Grader → Generator → HallucinationChecker. Self-corrects when retrieval quality is low."
              accent="#2563EB"
            />
            <FeatureCard
              icon="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"
              title="97% intent accuracy"
              desc="5-layer, 23-intent hybrid recognition. Rule shortcuts for speed, LLM for nuance. Tested across 30+ structured scenarios."
              accent="#059669"
            />
            <FeatureCard
              icon="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
              title="Smart knowledge base"
              desc="Semantic chunking keeps product info intact. Hybrid search (vector + BM25 + RRF) finds the right answer every time."
              accent="#7C3AED"
            />
            <FeatureCard
              icon="M16 11c1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3 1.34 3 3 3zm-8 0c1.66 0 3-1.34 3-3S9.66 5 8 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5z"
              title="Lead capture in conversation"
              desc="Naturally collects product needs, quantity, budget, and contact info during the chat. No forms, no friction."
              accent="#DB2777"
            />
            <FeatureCard
              icon="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0014.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12z"
              title="Multi-language auto-detect"
              desc="Ask in Chinese, get Chinese answers. Ask in English, get English. Automatic detection, no configuration needed."
              accent="#EA580C"
            />
            <FeatureCard
              icon="M3 3v18h18v-2H5V3H3zm16 10l-4-4-4 4-4-4-1.41 1.41L9 13.59l4-4 4 4 4-4V17h2V9z"
              title="Full pipeline observability"
              desc="See exactly how AI made each decision. Waterfall timeline shows every node's timing, LLM calls, and retrieval chunks."
              accent="#0891B2"
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" style={{ padding: '80px 32px', background: '#fff' }}>
        <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
          <div style={{
            display: 'inline-block', padding: '4px 14px', borderRadius: 8,
            background: '#ECFDF5', color: '#065F46', fontSize: 12, fontWeight: 600,
            letterSpacing: '.05em', textTransform: 'uppercase' as const, marginBottom: 12,
          }}>How it works</div>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 48, letterSpacing: '-0.02em' }}>
            Up and running in 5 minutes
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 40 }}>
            <StepCard num="1" title="Upload your docs" desc="PDF, Word, Excel, or paste a URL. Our semantic chunker keeps product info intact — no manual formatting needed." />
            <StepCard num="2" title="AI learns instantly" desc="Embedding + vector indexing happens in seconds. Add FAQ for common questions. Your knowledge base is live." />
            <StepCard num="3" title="Deploy anywhere" desc="Embed the chat widget on your website, share a standalone link, or connect WhatsApp and Telegram (coming soon)." />
          </div>
        </div>
      </section>

      {/* Technical edge */}
      <section style={{
        padding: '80px 32px',
        background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)',
        color: '#fff',
      }}>
        <div style={{ maxWidth: 900, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <h2 style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em' }}>
              Under the hood
            </h2>
            <p style={{ fontSize: 16, color: '#94A3B8', marginTop: 8 }}>
              What makes our AI different from a simple GPT wrapper
            </p>
          </div>

          <div style={{
            background: 'rgba(255,255,255,.04)', borderRadius: 16,
            border: '1px solid rgba(255,255,255,.08)', padding: '32px',
          }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
              {[
                { name: 'Router', desc: '23 intents', color: '#8B5CF6', ms: '50ms' },
                { name: 'QueryTransform', desc: 'HyDE / expand', color: '#06B6D4', ms: '0-2s' },
                { name: 'Retriever', desc: 'Vector+BM25+RRF', color: '#3B82F6', ms: '200ms' },
                { name: 'Grader', desc: 'Quality check', color: '#10B981', ms: '10ms' },
                { name: 'Generator', desc: 'Stream output', color: '#F59E0B', ms: '3-5s' },
                { name: 'HallucinationCheck', desc: 'Fact verify', color: '#EF4444', ms: 'async' },
              ].map((node, i) => (
                <div key={node.name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    padding: '12px 16px', borderRadius: 10,
                    background: node.color + '20', border: `1px solid ${node.color}40`,
                    minWidth: 100, textAlign: 'center',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: node.color }}>{node.name}</div>
                    <div style={{ fontSize: 10, color: '#94A3B8', marginTop: 2 }}>{node.desc}</div>
                    <div style={{ fontSize: 9, color: '#64748B', marginTop: 2 }}>{node.ms}</div>
                  </div>
                  {i < 5 && (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="#475569">
                      <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
                    </svg>
                  )}
                </div>
              ))}
            </div>

            <div style={{
              marginTop: 20, padding: '12px 16px', borderRadius: 8,
              background: 'rgba(239,68,68,.08)', border: '1px solid rgba(239,68,68,.15)',
              fontSize: 12, color: '#94A3B8', textAlign: 'center',
            }}>
              Grader score too low? → Auto re-retrieve with step-back query. Hallucination detected? → Block and clarify.
              <span style={{ color: '#60A5FA' }}> Self-correcting, not just answering.</span>
            </div>
          </div>
        </div>
      </section>

      {/* Compare */}
      <section id="compare" style={{ padding: '80px 32px', background: '#F8FAFC' }}>
        <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 40, letterSpacing: '-0.02em' }}>
            How we compare
          </h2>

          <div style={{
            background: '#fff', borderRadius: 16, border: '1px solid #E2E8F0',
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #E2E8F0' }}>
                  <th style={{ padding: '16px', textAlign: 'left', fontSize: 13, color: '#94A3B8', fontWeight: 500 }}>Capability</th>
                  <th style={{ padding: '16px', textAlign: 'center', fontSize: 13, color: '#2563EB', fontWeight: 600 }}>CS Platform</th>
                  <th style={{ padding: '16px', textAlign: 'center', fontSize: 13, color: '#94A3B8', fontWeight: 500 }}>Typical competitors</th>
                </tr>
              </thead>
              <tbody>
                <CompareRow feature="AI architecture" us="Agentic RAG (6-node)" them="GPT wrapper" />
                <CompareRow feature="Self-correction" us="Grader + re-retrieve" them="None" />
                <CompareRow feature="Hallucination check" us="Built-in async" them="None" />
                <CompareRow feature="Knowledge search" us="Vector + BM25 + RRF" them="Vector only" />
                <CompareRow feature="Intent recognition" us="5-layer / 23 intents" them="3-5 intents" />
                <CompareRow feature="Lead capture" us="Natural conversation" them="Rigid forms" />
                <CompareRow feature="Pipeline transparency" us="Full trace + waterfall" them="Black box" />
                <CompareRow feature="Setup time" us="5 minutes" them="Days to weeks" />
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{ padding: '80px 32px', background: '#fff' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 12, letterSpacing: '-0.02em' }}>
            Simple, affordable pricing
          </h2>
          <p style={{ fontSize: 16, color: '#64748B', marginBottom: 40 }}>
            Start free. Upgrade when you grow.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
            {[
              { name: 'Free', price: '¥0', period: '/forever', bots: '1 Bot', msgs: '200 msgs/mo', features: ['1 knowledge doc', 'Basic analytics', 'Widget embed'], cta: 'Start free', featured: false },
              { name: 'Trade', price: '¥299', period: '/month', bots: '3 Bots', msgs: '5,000 msgs/mo', features: ['Unlimited docs', 'Lead capture', 'Email notifications', 'Priority support'], cta: 'Get started', featured: true },
              { name: 'Pro', price: '¥799', period: '/month', bots: '10 Bots', msgs: '20,000 msgs/mo', features: ['Everything in Trade', 'Pipeline tracing', 'API access', 'Custom branding', 'Multi-channel (soon)'], cta: 'Contact us', featured: false },
            ].map(plan => (
              <div key={plan.name} style={{
                background: '#fff', borderRadius: 16, padding: '32px 24px',
                border: plan.featured ? '2px solid #2563EB' : '1px solid #E2E8F0',
                position: 'relative',
                boxShadow: plan.featured ? '0 8px 30px rgba(37,99,235,.08)' : 'none',
              }}>
                {plan.featured && (
                  <div style={{
                    position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                    background: '#2563EB', color: '#fff', fontSize: 11, fontWeight: 600,
                    padding: '4px 14px', borderRadius: 8,
                  }}>Most popular</div>
                )}
                <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 4 }}>{plan.name}</h3>
                <div style={{ marginBottom: 20 }}>
                  <span style={{ fontSize: 36, fontWeight: 700 }}>{plan.price}</span>
                  <span style={{ fontSize: 14, color: '#94A3B8' }}>{plan.period}</span>
                </div>
                <div style={{ fontSize: 13, color: '#64748B', marginBottom: 4 }}>{plan.bots}</div>
                <div style={{ fontSize: 13, color: '#64748B', marginBottom: 20 }}>{plan.msgs}</div>
                <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', textAlign: 'left' }}>
                  {plan.features.map(f => (
                    <li key={f} style={{ fontSize: 13, color: '#475569', padding: '4px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="#2563EB"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => navigate(plan.featured ? '/register' : '/demo')}
                  style={{
                    width: '100%', padding: '12px', borderRadius: 10, fontSize: 14, fontWeight: 500,
                    border: 'none', cursor: 'pointer',
                    background: plan.featured ? '#2563EB' : '#F1F5F9',
                    color: plan.featured ? '#fff' : '#334155',
                  }}
                >{plan.cta}</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{
        padding: '80px 32px', textAlign: 'center',
        background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)',
      }}>
        <h2 style={{ fontSize: 32, fontWeight: 700, color: '#fff', marginBottom: 12, letterSpacing: '-0.02em' }}>
          Ready to stop losing customers?
        </h2>
        <p style={{ fontSize: 16, color: '#94A3B8', marginBottom: 32, maxWidth: 480, margin: '0 auto 32px' }}>
          Try it yourself. No credit card, no sales call.
          Upload your docs and see the AI in action.
        </p>
        <div style={{ display: 'flex', gap: 14, justifyContent: 'center' }}>
          <button style={{ ...S.btnPrimary, padding: '14px 36px', fontSize: 16 }}
            onClick={() => navigate('/demo')}>Try live demo</button>
          <button style={{ ...S.btnOutline, padding: '14px 36px', fontSize: 16 }}
            onClick={() => navigate('/register')}>Create account</button>
        </div>
      </section>

      <footer style={{
        padding: '32px', background: '#0F172A', borderTop: '1px solid rgba(255,255,255,.06)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ ...S.logoIcon, width: 24, height: 24, borderRadius: 6 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="#fff"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
          </div>
          <span style={{ fontSize: 13, color: '#64748B' }}>CS Platform</span>
        </div>
        <span style={{ fontSize: 12, color: '#475569' }}>AI-powered customer service for SMEs</span>
      </footer>
    </div>
  )
}
