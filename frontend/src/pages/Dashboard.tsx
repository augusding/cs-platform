import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

interface Stats {
  total_sessions: number; resolved_rate: number
  no_hit_rate: number; avg_latency_ms: number
}
interface NoHitQuery { query: string; count: number; last_seen: string }
interface Session { id: string; visitor_id: string; status: string; started_at: string; message_count: number }
interface Bot { id: string; name: string; language: string; status: string; stats?: { chunk_total: number; faq_count: number } }

const PERIOD_OPTIONS = [
  { value: 'today', label: '今日' },
  { value: 'week',  label: '本周' },
  { value: 'month', label: '近30天' },
]

const STATUS_LABEL: Record<string, string> = {
  active: '进行中', ended: '已结束', transferred: '待接管'
}
const STATUS_BADGE: Record<string, string> = {
  active: 'badge badge-success', ended: 'badge badge-neutral', transferred: 'badge badge-warning'
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [stats, setStats]     = useState<Stats|null>(null)
  const [noHit, setNoHit]     = useState<NoHitQuery[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [bots, setBots]       = useState<Bot[]>([])
  const [period, setPeriod]   = useState('month')

  useEffect(() => {
    api.get(`/admin/stats?period=${period}`)
      .then(r => setStats(r.data.data)).catch(() => {})
  }, [period])

  useEffect(() => {
    api.get('/admin/no-hit-queries').then(r => setNoHit(r.data.data)).catch(() => {})
    api.get('/admin/sessions').then(r => setSessions(r.data.data || [])).catch(() => {})
    api.get('/bots').then(r => setBots(r.data.data || [])).catch(() => {})
  }, [])

  const METRICS = [
    {
      label: '本月会话',
      value: stats ? stats.total_sessions.toLocaleString() : '—',
      icon: 'M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z',
      iconBg: '#EFF6FF', iconColor: '#3B82F6',
    },
    {
      label: '解决率',
      value: stats ? `${(stats.resolved_rate * 100).toFixed(1)}%` : '—',
      icon: 'M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',
      iconBg: '#F0FDF4', iconColor: '#10B981',
    },
    {
      label: '无法回答率',
      value: stats ? `${(stats.no_hit_rate * 100).toFixed(1)}%` : '—',
      icon: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z',
      iconBg: '#FFFBEB', iconColor: '#F59E0B',
    },
    {
      label: '平均响应',
      value: stats?.avg_latency_ms ? `${stats.avg_latency_ms}ms` : '—',
      icon: 'M13 2.05v2.02c3.95.49 7 3.85 7 7.93 0 3.21-1.81 6-4.72 7.28L13 17v5l8-4.5V12c0-5.18-3.96-9.45-9-9.95z',
      iconBg: '#F5F3FF', iconColor: '#8B5CF6',
    },
  ]

  return (
    <div>
      {/* Period selector */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 2, background: '#F3F4F6', borderRadius: 8, padding: 3 }}>
          {PERIOD_OPTIONS.map(o => (
            <button key={o.value} onClick={() => setPeriod(o.value)} style={{
              padding: '5px 14px', border: 'none', borderRadius: 6, cursor: 'pointer',
              fontSize: 13, fontWeight: period === o.value ? 500 : 400,
              background: period === o.value ? '#fff' : 'transparent',
              color: period === o.value ? 'var(--text-primary)' : 'var(--text-muted)',
              boxShadow: period === o.value ? '0 1px 3px rgba(0,0,0,.08)' : 'none',
              transition: 'all .15s',
            }}>{o.label}</button>
          ))}
        </div>
      </div>

      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 16, marginBottom: 24 }}>
        {METRICS.map(m => (
          <div key={m.label} className="metric-card">
            <div className="metric-icon" style={{ background: m.iconBg }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill={m.iconColor}>
                <path d={m.icon} />
              </svg>
            </div>
            <div className="metric-label">{m.label}</div>
            <div className="metric-value">{m.value}</div>
          </div>
        ))}
      </div>

      {/* Sessions + No-hit */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">最近会话</span>
            <button className="btn-ghost" onClick={() => navigate('/sessions')}>全部 →</button>
          </div>
          {sessions.length === 0 ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              暂无会话数据
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>访客</th><th>消息数</th><th>状态</th><th>时间</th>
                </tr>
              </thead>
              <tbody>
                {sessions.slice(0, 5).map(s => (
                  <tr key={s.id} onClick={() => navigate(`/sessions/${s.id}`)}>
                    <td style={{ fontWeight: 500 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className={`dot ${s.status === 'active' ? 'dot-green' : s.status === 'transferred' ? 'dot-amber' : 'dot-gray'}`} />
                        {s.visitor_id.slice(0, 12)}…
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{s.message_count}</td>
                    <td><span className={STATUS_BADGE[s.status] || 'badge badge-neutral'}>{STATUS_LABEL[s.status] || s.status}</span></td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      {new Date(s.started_at).toLocaleTimeString('zh', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">未解决问题</span>
            <button className="btn-ghost" onClick={() => navigate('/knowledge')}>补充知识库 →</button>
          </div>
          {noHit.length === 0 ? (
            <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              暂无未解决问题
            </div>
          ) : (
            <div>
              {noHit.slice(0, 6).map((q, i) => {
                const maxCount = noHit[0]?.count || 1
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '11px 20px', borderBottom: i < 5 ? '1px solid var(--border-light)' : 'none',
                  }}>
                    <div style={{ flex: 1, fontSize: 13, color: 'var(--text-primary)', minWidth: 0 }}>
                      <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{q.query}</div>
                    </div>
                    <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 50, height: 4, background: '#F3F4F6', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: '#FCA5A5', borderRadius: 2, width: `${(q.count / maxCount) * 100}%` }} />
                      </div>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', minWidth: 28, textAlign: 'right' }}>{q.count}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Bots */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <span className="section-title">Bot 状态</span>
        <button className="btn-ghost" onClick={() => navigate('/bots')}>管理全部 →</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
        {bots.map(bot => (
          <div key={bot.id} className="card" style={{ cursor: 'pointer', transition: 'border-color .15s' }}
            onClick={() => navigate(`/bots/${bot.id}`)}
            onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.borderColor = '#93C5FD'}
            onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'}
          >
            <div style={{ padding: '16px 18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, background: 'var(--accent-light)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 20, flexShrink: 0,
                }}>🤖</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{bot.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 1 }}>
                    {bot.language === 'zh' ? '中文' : bot.language === 'en' ? 'English' : '双语'}
                  </div>
                </div>
                <span className={`badge ${bot.status === 'active' ? 'badge-success' : 'badge-neutral'}`}>
                  {bot.status === 'active' ? '运行中' : '已停用'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: 16, paddingTop: 12, borderTop: '1px solid var(--border-light)' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {bot.stats?.chunk_total ?? '—'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>chunks</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {bot.stats?.faq_count ?? '—'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>FAQ</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
