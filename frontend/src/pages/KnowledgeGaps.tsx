import { useEffect, useState, useCallback } from 'react'
import api from '../api/client'

interface Gap {
  id: string
  bot_id: string
  bot_name: string
  cluster_label: string
  sample_queries: string[]
  query_count: number
  unique_sessions: number
  avg_grader_score: number
  primary_signal: string
  signal_breakdown: Record<string, number>
  suggested_content: string
  status: string
  first_seen: string
  last_seen: string
}

interface Summary {
  open_count: number
  resolved_count: number
  dismissed_count: number
  total_affected_queries: number
  total_affected_sessions: number
}

const SIGNAL_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  out_of_scope:  { label: 'Out of scope',         color: '#6B7280', bg: '#F3F4F6' },
  low_grader:    { label: 'Low relevance',        color: '#D97706', bg: '#FFFBEB' },
  transfer:      { label: 'Transfer to human',    color: '#DC2626', bg: '#FEF2F2' },
  hallucination: { label: 'Hallucination',        color: '#7C3AED', bg: '#F5F3FF' },
  clarification: { label: 'Needed clarification', color: '#2563EB', bg: '#EFF6FF' },
}

export default function KnowledgeGaps() {
  const [gaps, setGaps] = useState<Gap[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [statusFilter, setStatusFilter] = useState('open')
  const [expanded, setExpanded] = useState<string | null>(null)

  const [faqModal, setFaqModal] = useState<{ gapId: string; queries: string[] } | null>(null)
  const [faqQuestion, setFaqQuestion] = useState('')
  const [faqAnswer, setFaqAnswer] = useState('')
  const [faqSaving, setFaqSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [gapsResp, summaryResp] = await Promise.all([
        api.get(`/admin/gaps?status=${statusFilter}`),
        api.get('/admin/gaps/summary'),
      ])
      setGaps(gapsResp.data.data || [])
      setSummary(summaryResp.data.summary || null)
    } catch (e) {
      console.error('gaps load error', e)
    }
    setLoading(false)
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const triggerAnalysis = async () => {
    setAnalyzing(true)
    try {
      const botsResp = await api.get('/bots')
      const bots = botsResp.data.data || []
      for (const bot of bots) {
        await api.post('/admin/gaps/analyze', { bot_id: bot.id, days: 30 })
      }
      await load()
    } catch (e) {
      console.error('analysis error', e)
    }
    setAnalyzing(false)
  }

  const updateStatus = async (gapId: string, status: string, reason?: string) => {
    try {
      await api.put(`/admin/gaps/${gapId}`, { status, reason })
      setGaps(prev => prev.filter(g => g.id !== gapId))
      const summaryResp = await api.get('/admin/gaps/summary')
      setSummary(summaryResp.data.summary || null)
    } catch (e) {
      console.error('update error', e)
    }
  }

  const openFaqModal = (gap: Gap) => {
    setFaqModal({ gapId: gap.id, queries: gap.sample_queries })
    setFaqQuestion(gap.sample_queries[0] || '')
    setFaqAnswer(gap.suggested_content || '')
  }

  const submitFaq = async () => {
    if (!faqModal || !faqQuestion.trim() || !faqAnswer.trim()) return
    setFaqSaving(true)
    try {
      await api.post(`/admin/gaps/${faqModal.gapId}/add-faq`, {
        question: faqQuestion, answer: faqAnswer,
      })
      setFaqModal(null)
      await load()
    } catch (e) {
      console.error('add faq error', e)
    }
    setFaqSaving(false)
  }

  return (
    <div>
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          {[
            { label: 'Open gaps', value: summary.open_count, color: summary.open_count > 0 ? '#DC2626' : '#059669' },
            { label: 'Affected queries', value: summary.total_affected_queries, color: '#D97706' },
            { label: 'Affected sessions', value: summary.total_affected_sessions, color: '#2563EB' },
            { label: 'Resolved', value: summary.resolved_count, color: '#059669' },
          ].map(c => (
            <div key={c.label} style={{
              background: '#fff', borderRadius: 8, padding: '14px 18px',
              border: '1px solid var(--border)',
            }}>
              <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{c.label}</div>
              <div style={{ fontSize: 22, fontWeight: 600, color: c.color }}>{c.value}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <select className="input" style={{ width: 140, height: 34, fontSize: 12 }}
          value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>

        <button className="btn-primary" style={{ height: 34, fontSize: 12, padding: '0 16px' }}
          onClick={triggerAnalysis} disabled={analyzing}>
          {analyzing ? 'Analyzing...' : 'Run analysis'}
        </button>

        <button className="btn-ghost" style={{ height: 34, fontSize: 12 }} onClick={load}>
          Refresh
        </button>

        <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 'auto' }}>
          {gaps.length} gaps
        </span>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>Loading...</div>
      ) : gaps.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 60, background: '#fff', borderRadius: 12,
          border: '1px solid var(--border)',
        }}>
          <div style={{ fontSize: 14, color: '#6B7280', marginBottom: 4 }}>
            {statusFilter === 'open' ? 'No open knowledge gaps' : `No ${statusFilter} gaps`}
          </div>
          <div style={{ fontSize: 12, color: '#9CA3AF' }}>
            {statusFilter === 'open'
              ? 'Click "Run analysis" to scan recent conversations for knowledge gaps'
              : ''}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {gaps.map(gap => {
            const signal = SIGNAL_LABELS[gap.primary_signal] || SIGNAL_LABELS.low_grader
            const isExpanded = expanded === gap.id
            return (
              <div key={gap.id} style={{
                background: '#fff', borderRadius: 10, border: '1px solid var(--border)',
                overflow: 'hidden',
              }}>
                <div style={{
                  padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12,
                  cursor: 'pointer',
                }}
                  onClick={() => setExpanded(isExpanded ? null : gap.id)}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: '#111827' }}>
                        {gap.cluster_label}
                      </span>
                      <span style={{
                        fontSize: 10, padding: '2px 8px', borderRadius: 6,
                        background: signal.bg, color: signal.color, fontWeight: 500,
                      }}>{signal.label}</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#9CA3AF' }}>
                      {gap.query_count} queries · {gap.unique_sessions} sessions
                      · avg grader {gap.avg_grader_score?.toFixed(2)}
                      {gap.bot_name && <> · {gap.bot_name}</>}
                    </div>
                  </div>

                  {statusFilter === 'open' && (
                    <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                      <button className="btn-primary" style={{ fontSize: 11, padding: '4px 12px', height: 28 }}
                        onClick={() => openFaqModal(gap)}>
                        Add FAQ
                      </button>
                      <button className="btn-ghost" style={{ fontSize: 11, padding: '4px 10px', height: 28 }}
                        onClick={() => updateStatus(gap.id, 'dismissed', 'Not relevant')}>
                        Dismiss
                      </button>
                    </div>
                  )}

                  <svg width="16" height="16" viewBox="0 0 24 24" fill="#9CA3AF"
                    style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}>
                    <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>
                  </svg>
                </div>

                {isExpanded && (
                  <div style={{
                    padding: '0 18px 16px', borderTop: '1px solid #F3F4F6',
                  }}>
                    <div style={{ marginTop: 12, marginBottom: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 6 }}>
                        Sample queries
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                        {gap.sample_queries.map((q, i) => (
                          <div key={i} style={{
                            fontSize: 12, padding: '6px 10px', borderRadius: 6,
                            background: '#F9FAFB', color: '#374151',
                          }}>"{q}"</div>
                        ))}
                      </div>
                    </div>

                    {gap.suggested_content && (
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 600, color: '#6B7280', marginBottom: 6 }}>
                          Suggested content to add
                        </div>
                        <div style={{
                          fontSize: 12, padding: '10px 14px', borderRadius: 8,
                          background: '#EFF6FF', border: '1px solid #BFDBFE',
                          color: '#1E40AF', lineHeight: 1.7, whiteSpace: 'pre-wrap',
                        }}>
                          {gap.suggested_content}
                        </div>
                      </div>
                    )}

                    <div style={{ fontSize: 10, color: '#C4C4C4', marginTop: 10 }}>
                      First seen: {gap.first_seen?.slice(0, 16)} · Last seen: {gap.last_seen?.slice(0, 16)}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {faqModal && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }} onClick={() => setFaqModal(null)}>
          <div style={{
            background: '#fff', borderRadius: 12, padding: '24px', width: 500,
            maxHeight: '80vh', overflowY: 'auto',
          }} onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Add FAQ from knowledge gap</h3>

            <label style={{ fontSize: 12, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 4 }}>
              Question
            </label>
            <input className="input" value={faqQuestion}
              onChange={e => setFaqQuestion(e.target.value)}
              style={{ marginBottom: 12 }} />

            <label style={{ fontSize: 12, fontWeight: 500, color: '#374151', display: 'block', marginBottom: 4 }}>
              Answer
            </label>
            <textarea className="input" rows={6} value={faqAnswer}
              onChange={e => setFaqAnswer(e.target.value)}
              style={{ marginBottom: 16 }} />

            <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 12 }}>
              Related queries: {faqModal.queries.map(q => `"${q}"`).join(', ')}
            </div>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn-ghost" onClick={() => setFaqModal(null)}>Cancel</button>
              <button className="btn-primary" onClick={submitFaq} disabled={faqSaving}>
                {faqSaving ? 'Adding...' : 'Add FAQ & resolve gap'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
