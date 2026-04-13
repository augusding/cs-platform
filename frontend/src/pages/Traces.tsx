import { Fragment, useEffect, useState, useCallback } from 'react'
import api from '../api/client'

interface TraceRow {
  trace_id: string
  session_id: string
  bot_id: string
  channel: string
  user_query: string
  intent: string
  intent_confidence: number
  grader_score: number
  cache_hit: boolean
  total_latency_ms: number
  llm_calls_count: number
  llm_total_tokens: number
  retrieval_chunks: number
  exit_branch: string
  answer_preview: string
  created_at: string
}

interface SpanRow {
  parent_span_id: string | null
  node: string
  operation: string
  start_ms: number
  end_ms: number
  duration_ms: number
  offset_ms: number
  status: string
  error_msg: string
  attributes: Record<string, any>
}

interface Stats {
  total_requests: number
  avg_latency_ms: number
  p95_latency_ms: number
  avg_grader_score: number
  cache_hits: number
  transfers: number
  total_tokens: number
  avg_llm_calls: number
  hallucination_failures: number
}

const NODE_COLORS: Record<string, string> = {
  cache_check:           '#94A3B8',
  router:                '#8B5CF6',
  llm_call:              '#F59E0B',
  query_transform:       '#06B6D4',
  retriever:             '#3B82F6',
  faq_search:            '#60A5FA',
  vector_search:         '#2563EB',
  retriever_merge:       '#1D4ED8',
  grader:                '#10B981',
  generator:             '#EF4444',
  hallucination_checker: '#F97316',
  post_process:          '#6B7280',
}

const EXIT_COLORS: Record<string, string> = {
  cache_hit:      '#10B981',
  skip_retrieval: '#06B6D4',
  full_rag:       '#3B82F6',
  lead_capture:   '#F59E0B',
  transfer:       '#EF4444',
  out_of_scope:   '#6B7280',
  clarification:  '#8B5CF6',
  error:          '#DC2626',
}

function WaterfallChart({ spans, totalMs }: { spans: SpanRow[]; totalMs: number }) {
  if (!spans.length || !totalMs) return null
  const maxWidth = 600
  const barHeight = 24
  const gap = 4
  const height = spans.length * (barHeight + gap) + 20

  return (
    <div style={{ overflowX: 'auto', padding: '8px 0' }}>
      <svg width={maxWidth + 200} height={height} style={{ fontFamily: 'monospace', fontSize: 11 }}>
        {[0, 0.25, 0.5, 0.75, 1].map(pct => {
          const x = 140 + pct * maxWidth
          const ms = Math.round(pct * totalMs)
          return (
            <g key={pct}>
              <line x1={x} y1={0} x2={x} y2={height} stroke="#E5E7EB" strokeDasharray="2,2" />
              <text x={x} y={12} fill="#9CA3AF" textAnchor="middle">{ms}ms</text>
            </g>
          )
        })}

        {spans.map((s, i) => {
          const y = 20 + i * (barHeight + gap)
          const x = 140 + (s.offset_ms / totalMs) * maxWidth
          const w = Math.max((s.duration_ms / totalMs) * maxWidth, 2)
          const color = NODE_COLORS[s.node] || NODE_COLORS[s.operation] || '#94A3B8'
          const isError = s.status === 'error'
          const label = s.node === 'llm_call' ? s.operation : s.node
          const indent = s.parent_span_id ? '  └ ' : ''

          return (
            <g key={i}>
              <text x={4} y={y + 16} fill="#374151" style={{ fontSize: 10 }}>
                {indent}{label}
              </text>
              <rect x={x} y={y + 2} width={w} height={barHeight - 4}
                rx={3} fill={isError ? '#FEE2E2' : color} opacity={isError ? 1 : 0.8} />
              {s.duration_ms > 0 && (
                <text x={x + w + 4} y={y + 16} fill="#6B7280" style={{ fontSize: 10 }}>
                  {s.duration_ms}ms
                  {s.node === 'llm_call' && s.attributes?.tokens_out
                    ? ` (${s.attributes.tokens_out}tok)`
                    : ''}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function TraceDetail({ traceId }: { traceId: string }) {
  const [data, setData] = useState<{ trace: any; spans: SpanRow[] } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/admin/traces/${traceId}`).then(r => {
      setData(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [traceId])

  if (loading) return <div style={{ padding: 16, color: '#9CA3AF' }}>加载中...</div>
  if (!data) return <div style={{ padding: 16, color: '#EF4444' }}>加载失败</div>

  const { trace, spans } = data

  return (
    <div style={{ padding: '12px 16px', background: '#FAFBFC', borderTop: '1px solid #E5E7EB' }}>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12, fontSize: 12 }}>
        <span><b>Exit:</b> {trace.exit_branch}</span>
        <span><b>Intent:</b> {trace.intent} ({((trace.intent_confidence || 0) * 100).toFixed(0)}%)</span>
        <span><b>Grader:</b> {(trace.grader_score || 0).toFixed(3)}</span>
        <span><b>Chunks:</b> {trace.retrieval_chunks}</span>
        <span><b>LLM Calls:</b> {trace.llm_calls_count}</span>
        <span><b>Tokens:</b> {trace.llm_total_tokens}</span>
        <span><b>Cache:</b> {trace.cache_hit ? '✓ HIT' : '✗ MISS'}</span>
      </div>

      <WaterfallChart spans={spans} totalMs={trace.total_latency_ms || 1} />

      {trace.answer_preview && (
        <div style={{ marginTop: 8, padding: '8px 12px', background: '#fff', borderRadius: 6,
                       border: '1px solid #E5E7EB', fontSize: 12, color: '#374151' }}>
          <b>回答：</b>{trace.answer_preview}
        </div>
      )}

      <details style={{ marginTop: 8 }}>
        <summary style={{ cursor: 'pointer', fontSize: 12, color: '#6B7280' }}>
          展开 {spans.length} 个 Span 详情
        </summary>
        <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', marginTop: 4 }}>
          <thead>
            <tr style={{ background: '#F3F4F6' }}>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Node</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Operation</th>
              <th style={{ textAlign: 'right', padding: '4px 8px' }}>Duration</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Status</th>
              <th style={{ textAlign: 'left', padding: '4px 8px' }}>Attributes</th>
            </tr>
          </thead>
          <tbody>
            {spans.map((s, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #F3F4F6' }}>
                <td style={{ padding: '3px 8px', fontFamily: 'monospace' }}>{s.node}</td>
                <td style={{ padding: '3px 8px' }}>{s.operation}</td>
                <td style={{ padding: '3px 8px', textAlign: 'right', fontFamily: 'monospace' }}>
                  {s.duration_ms}ms
                </td>
                <td style={{ padding: '3px 8px' }}>
                  <span style={{
                    padding: '1px 6px', borderRadius: 4, fontSize: 10,
                    background: s.status === 'ok' ? '#ECFDF5' : '#FEF2F2',
                    color: s.status === 'ok' ? '#065F46' : '#991B1B',
                  }}>{s.status}</span>
                </td>
                <td style={{ padding: '3px 8px', fontSize: 10, color: '#6B7280', maxWidth: 300,
                             overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {JSON.stringify(s.attributes).slice(0, 120)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}

function StatsCards({ stats }: { stats: Stats | null }) {
  if (!stats) return null

  const cards: Array<{ label: string; value: any; unit: string; color?: string }> = [
    { label: '总请求数', value: stats.total_requests, unit: '' },
    { label: '平均延迟', value: stats.avg_latency_ms, unit: 'ms',
      color: stats.avg_latency_ms > 5000 ? '#EF4444' : undefined },
    { label: 'P95 延迟', value: stats.p95_latency_ms, unit: 'ms',
      color: stats.p95_latency_ms > 8000 ? '#EF4444' : undefined },
    { label: 'Grader 均分', value: (stats.avg_grader_score || 0).toFixed(2), unit: '',
      color: stats.avg_grader_score < 0.5 ? '#EF4444' : undefined },
    { label: '缓存命中', value: stats.total_requests
        ? `${((stats.cache_hits / stats.total_requests) * 100).toFixed(0)}%`
        : '0%', unit: '' },
    { label: 'Token 消耗', value: (stats.total_tokens || 0).toLocaleString(), unit: '' },
    { label: '转人工', value: stats.transfers, unit: '' },
    { label: '幻觉失败', value: stats.hallucination_failures, unit: '',
      color: stats.hallucination_failures > 0 ? '#F59E0B' : undefined },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
      {cards.map(c => (
        <div key={c.label} style={{
          background: '#fff', borderRadius: 8, padding: '12px 16px',
          border: '1px solid #E5E7EB',
        }}>
          <div style={{ fontSize: 11, color: '#9CA3AF', marginBottom: 4 }}>{c.label}</div>
          <div style={{ fontSize: 20, fontWeight: 600, color: c.color || '#111827' }}>
            {c.value}{c.unit && <span style={{ fontSize: 12, color: '#9CA3AF' }}> {c.unit}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Traces() {
  const [traces, setTraces] = useState<TraceRow[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  const [intentFilter, setIntentFilter] = useState('')
  const [exitFilter, setExitFilter] = useState('')
  const [minLatency, setMinLatency] = useState('')

  const limit = 30

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('limit', String(limit))
      params.set('offset', String(offset))
      if (intentFilter) params.set('intent', intentFilter)
      if (exitFilter) params.set('exit_branch', exitFilter)
      if (minLatency) params.set('min_latency', minLatency)

      const [traceResp, statsResp] = await Promise.all([
        api.get(`/admin/traces?${params}`),
        api.get('/admin/traces/stats?hours=24'),
      ])
      setTraces(traceResp.data.data || [])
      setTotal(traceResp.data.total || 0)
      setStats(statsResp.data.summary || null)
    } catch (e) {
      console.error('traces load error', e)
    }
    setLoading(false)
  }, [offset, intentFilter, exitFilter, minLatency])

  useEffect(() => { load() }, [load])

  const toggleExpand = (traceId: string) => {
    setExpanded(prev => prev === traceId ? null : traceId)
  }

  return (
    <div>
      <StatsCards stats={stats} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <select className="input" style={{ width: 140, height: 32, fontSize: 12 }}
          value={intentFilter} onChange={e => { setIntentFilter(e.target.value); setOffset(0) }}>
          <option value="">全部意图</option>
          {['greeting','product_info','price_inquiry','purchase_intent','complaint',
            'transfer_explicit','out_of_scope','chitchat','how_to_use','availability'].map(i =>
            <option key={i} value={i}>{i}</option>
          )}
        </select>

        <select className="input" style={{ width: 140, height: 32, fontSize: 12 }}
          value={exitFilter} onChange={e => { setExitFilter(e.target.value); setOffset(0) }}>
          <option value="">全部分支</option>
          {['cache_hit','skip_retrieval','full_rag','lead_capture','transfer',
            'out_of_scope','clarification'].map(e =>
            <option key={e} value={e}>{e}</option>
          )}
        </select>

        <input className="input" style={{ width: 120, height: 32, fontSize: 12 }}
          placeholder="最小延迟(ms)" value={minLatency}
          onChange={e => setMinLatency(e.target.value)}
          onBlur={() => { setOffset(0); load() }}
          onKeyDown={e => { if (e.key === 'Enter') { setOffset(0); load() } }}
        />

        <button className="btn-ghost" style={{ height: 32, fontSize: 12 }} onClick={load}>
          刷新
        </button>

        <span style={{ fontSize: 12, color: '#9CA3AF', marginLeft: 'auto' }}>
          共 {total} 条
        </span>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>加载中...</div>
      ) : traces.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#9CA3AF' }}>
          暂无数据，发送一条对话消息后刷新
        </div>
      ) : (
        <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #E5E7EB', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500 }}>时间</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500 }}>问题</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500 }}>意图</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', fontWeight: 500 }}>延迟</th>
                <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 500 }}>LLM</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', fontWeight: 500 }}>Exit</th>
                <th style={{ textAlign: 'center', padding: '8px 12px', fontWeight: 500 }}>缓存</th>
              </tr>
            </thead>
            <tbody>
              {traces.map(t => (
                <Fragment key={t.trace_id}>
                  <tr
                    onClick={() => toggleExpand(t.trace_id)}
                    style={{ cursor: 'pointer', borderBottom: '1px solid #F3F4F6',
                             background: expanded === t.trace_id ? '#F0F7FF' : '#fff' }}
                    onMouseEnter={e => { if (expanded !== t.trace_id) (e.currentTarget as HTMLTableRowElement).style.background = '#FAFBFC' }}
                    onMouseLeave={e => { if (expanded !== t.trace_id) (e.currentTarget as HTMLTableRowElement).style.background = '#fff' }}
                  >
                    <td style={{ padding: '8px 12px', color: '#6B7280', whiteSpace: 'nowrap' }}>
                      {t.created_at?.slice(11, 19)}
                    </td>
                    <td style={{ padding: '8px 12px', maxWidth: 250, overflow: 'hidden',
                                 textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {t.user_query}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 11,
                                      background: '#EFF6FF', color: '#1D4ED8' }}>
                        {t.intent}
                      </span>
                      <span style={{ fontSize: 10, color: '#9CA3AF', marginLeft: 4 }}>
                        {((t.intent_confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'monospace',
                                 color: t.total_latency_ms > 5000 ? '#EF4444' : '#374151' }}>
                      {(t.total_latency_ms / 1000).toFixed(1)}s
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      {t.llm_calls_count}×
                      <span style={{ fontSize: 10, color: '#9CA3AF' }}> {t.llm_total_tokens}tok</span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ padding: '2px 6px', borderRadius: 4, fontSize: 10,
                                      background: EXIT_COLORS[t.exit_branch] || '#6B7280',
                                      color: '#fff' }}>
                        {t.exit_branch}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      {t.cache_hit ? '✓' : ''}
                    </td>
                  </tr>
                  {expanded === t.trace_id && (
                    <tr>
                      <td colSpan={7} style={{ padding: 0 }}>
                        <TraceDetail traceId={t.trace_id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>

          {total > limit && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: 12, padding: '12px 0',
                           borderTop: '1px solid #E5E7EB' }}>
              <button className="btn-ghost" style={{ fontSize: 12 }}
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}>
                上一页
              </button>
              <span style={{ fontSize: 12, color: '#6B7280', lineHeight: '32px' }}>
                {offset + 1}-{Math.min(offset + limit, total)} / {total}
              </span>
              <button className="btn-ghost" style={{ fontSize: 12 }}
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}>
                下一页
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
