import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

interface BotConfig {
  id: string; name: string; welcome_message: string; language: string
  style: string; system_prompt: string; avatar_url: string
  private_domain_config: any
  is_demo?: boolean
  stats?: { chunk_total: number; faq_count: number }
}

interface DebugInfo {
  intent: string; transform_strategy: string
  grader_score: number; grader_threshold: number
  attempts: number; is_grounded: boolean
  hallucination: string; should_transfer: boolean
  chunks: { index: number; source: string; page: number; score: number; preview: string }[]
  tokens_used: number
  pipeline_trace?: any[]
  transformed_query?: string
  intent_confidence?: number
  intent_reason?: string
}

interface ChatMsg {
  role: 'user' | 'bot' | 'system'
  content: string
  debug?: DebugInfo
  latency_ms?: number
  cache_hit?: boolean
}

const STYLE_OPTIONS = [
  { value: 'friendly',     label: '友好亲切' },
  { value: 'professional', label: '简洁高效' },
  { value: 'humanized',    label: '拟人对话' },
]
const INTENT_COLOR: Record<string, string> = {
  // L1
  greeting:       'bg-green-50 text-green-600',
  farewell:       'bg-green-50 text-green-600',
  acknowledgment: 'bg-green-50 text-green-600',
  bot_identity:   'bg-purple-50 text-purple-600',
  capability:     'bg-purple-50 text-purple-600',
  chitchat:       'bg-gray-100 text-gray-500',
  // L2
  product_info:   'bg-blue-50 text-blue-600',
  price_inquiry:  'bg-blue-50 text-blue-600',
  availability:   'bg-blue-50 text-blue-600',
  how_to_use:     'bg-blue-50 text-blue-600',
  policy_query:   'bg-blue-50 text-blue-600',
  comparison:     'bg-blue-50 text-blue-600',
  // L3
  purchase_intent:'bg-amber-50 text-amber-600',
  bulk_inquiry:   'bg-amber-50 text-amber-600',
  custom_request: 'bg-amber-50 text-amber-600',
  lead_capture:   'bg-amber-50 text-amber-600',
  // L4
  complaint:          'bg-red-50 text-red-500',
  urgent:             'bg-red-50 text-red-500',
  transfer_explicit:  'bg-red-50 text-red-500',
  transfer_implicit:  'bg-red-50 text-red-500',
  // L5
  clarification:  'bg-yellow-50 text-yellow-600',
  follow_up:      'bg-gray-100 text-gray-500',
  multi_intent:   'bg-indigo-50 text-indigo-600',
  out_of_scope:   'bg-gray-100 text-gray-500',
  // legacy compat
  knowledge_qa:   'bg-blue-50 text-blue-600',
  transfer:       'bg-red-50 text-red-500',
}
const DEBUG_TABS = ['对话测试', 'RAG 详情', '历史记录'] as const
type DebugTab = typeof DEBUG_TABS[number]

export default function BotDetail() {
  const { botId }  = useParams<{ botId: string }>()
  const navigate   = useNavigate()
  const [bot, setBot]       = useState<BotConfig | null>(null)
  const [form, setForm]     = useState<Partial<BotConfig>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved]   = useState(false)
  const [error, setError]   = useState('')
  const [pdEnabled, setPdEnabled] = useState(false)
  const [isDemo, setIsDemo] = useState(false)
  const [embedCode, setEmbedCode] = useState('')
  const [showEmbed, setShowEmbed] = useState(false)
  const [copied, setCopied] = useState(false)

  // Debug panel
  const [debugTab, setDebugTab]   = useState<DebugTab>('对话测试')
  const [messages, setMessages]   = useState<ChatMsg[]>([])
  const [inputVal, setInputVal]   = useState('')
  const [sending, setSending]     = useState(false)
  const [lastDebug, setLastDebug] = useState<DebugInfo | null>(null)
  const wsRef    = useRef<WebSocket | null>(null)
  const msgsRef  = useRef<HTMLDivElement>(null)
  const tokenBuf = useRef<string>('')

  useEffect(() => {
    if (!botId) return
    api.get(`/bots/${botId}/detail`).then(r => {
      const b = r.data.data
      setBot(b)
      setForm({
        name: b.name, welcome_message: b.welcome_message,
        language: b.language, style: b.style,
        system_prompt: b.system_prompt || '',
        avatar_url: b.avatar_url || '',
        private_domain_config: b.private_domain_config || {},
      })
      setPdEnabled(!!(b.private_domain_config?.enabled))
      setIsDemo(!!b.is_demo)
    })
  }, [botId])

  // Debug WS
  useEffect(() => {
    if (!botId) return
    const token = localStorage.getItem('access_token')
    if (!token) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host  = window.location.hostname
    const port  = window.location.port === '3001' ? '8081' : window.location.port
    const ws = new WebSocket(`${proto}://${host}:${port}/api/admin/debug/${botId}?token=${token}`)
    wsRef.current = ws

    ws.onmessage = e => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'connected') {
        setMessages([{ role: 'system', content: `已连接 · ${msg.bot_name}` }])
        if (msg.welcome) {
          setMessages(prev => [...prev, { role: 'bot', content: msg.welcome }])
        }
      } else if (msg.type === 'token') {
        tokenBuf.current += msg.content
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === 'bot' && last.content === '…') {
            return [...prev.slice(0, -1), { role: 'bot', content: tokenBuf.current }]
          }
          if (last?.role === 'bot') {
            return [...prev.slice(0, -1), { role: 'bot', content: tokenBuf.current }]
          }
          return prev
        })
        setTimeout(() => msgsRef.current?.scrollTo(0, msgsRef.current.scrollHeight), 10)
      } else if (msg.type === 'done') {
        tokenBuf.current = ''
        setSending(false)
        setLastDebug(msg.debug)
        setMessages(prev => {
          const updated = [...prev]
          const lastIdx = updated.length - 1
          if (updated[lastIdx]?.role === 'bot') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              debug:      msg.debug,
              latency_ms: msg.latency_ms,
              cache_hit:  msg.cache_hit,
            }
          }
          return updated
        })
      } else if (msg.type === 'error') {
        tokenBuf.current = ''
        setSending(false)
        setMessages(prev => [...prev.filter(m => m.content !== '…'),
          { role: 'bot', content: `错误：${msg.message}` }])
      } else if (msg.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
      }
    }

    ws.onclose = () => {
      setMessages(prev => [...prev, { role: 'system', content: '连接已断开' }])
    }

    return () => ws.close()
  }, [botId])

  const sendDebugMsg = () => {
    const text = inputVal.trim()
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || sending) return
    setSending(true)
    tokenBuf.current = ''
    setMessages(prev => [...prev,
      { role: 'user', content: text },
      { role: 'bot',  content: '…' },
    ])
    setInputVal('')
    wsRef.current.send(JSON.stringify({ type: 'message', content: text }))
    setTimeout(() => msgsRef.current?.scrollTo(0, msgsRef.current.scrollHeight), 10)
  }

  const save = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      const payload: any = { ...form }
      payload.private_domain_config = pdEnabled
        ? { ...(form.private_domain_config || {}), enabled: true }
        : null
      payload.is_demo = isDemo
      await api.put(`/bots/${botId}`, payload)
      setSaved(true); setTimeout(() => setSaved(false), 2000)
    } catch (e: any) {
      setError(e.response?.data?.reason || e.userMessage || '保存失败')
    } finally { setSaving(false) }
  }

  const getEmbed = async () => {
    try {
      const { data } = await api.post(`/bots/${botId}/reveal-key`)
      setEmbedCode(data.data.embed_code)
      setShowEmbed(true)
    } catch (e: any) { alert(e.userMessage || '获取失败') }
  }

  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))
  const setPd = (k: string, v: any) =>
    setForm(f => ({ ...f, private_domain_config: { ...(f.private_domain_config || {}), [k]: v } }))

  if (!bot) return <div className="text-gray-400 text-sm p-8">加载中...</div>

  return (
    <div>
      {/* 顶部导航 */}
      <div className="flex items-center gap-2 mb-5">
        <button onClick={() => navigate('/bots')} className="text-sm text-gray-500 hover:text-gray-700">← Bot 列表</button>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-medium text-gray-800">{bot.name}</span>
        <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full ml-1">运行中</span>
      </div>

      {/* 统计 */}
      {bot.stats && (
        <div className="grid grid-cols-2 gap-3 mb-5 max-w-xs">
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
            <p className="text-2xl font-semibold text-blue-600">{bot.stats.chunk_total}</p>
            <p className="text-xs text-gray-400 mt-1">知识库 Chunks</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
            <p className="text-2xl font-semibold text-green-600">{bot.stats.faq_count}</p>
            <p className="text-xs text-gray-400 mt-1">FAQ 条目</p>
          </div>
        </div>
      )}

      {/* 主体：左右布局 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', alignItems: 'start' }}>

        {/* 左侧：配置 */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-medium text-gray-800 mb-4">基础配置</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Bot 名称 *</label>
                <input className="input" value={form.name||''} onChange={e => set('name', e.target.value)} />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">欢迎语</label>
                <input className="input" value={form.welcome_message||''} onChange={e => set('welcome_message', e.target.value)} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">语言</label>
                  <select className="input" value={form.language||'zh'} onChange={e => set('language', e.target.value)}>
                    <option value="zh">中文</option>
                    <option value="en">English</option>
                    <option value="both">双语</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">对话风格</label>
                  <select className="input" value={form.style||'friendly'} onChange={e => set('style', e.target.value)}>
                    {STYLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                </div>
              </div>
              {form.style === 'humanized' && (
                <p className="text-xs text-amber-600 mt-1">
                  拟人模式：AI 会用口语化风格回答，不使用列表格式，主动追问客户，体验最接近真人客服
                </p>
              )}
              {form.style === 'professional' && (
                <p className="text-xs text-gray-400 mt-1">
                  信息密度高，结构化输出，适合 B2B 采购场景
                </p>
              )}
              {(!form.style || form.style === 'friendly') && (
                <p className="text-xs text-gray-400 mt-1">
                  友好热情，适当使用语气词，平衡信息完整度和亲和力
                </p>
              )}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">自定义系统提示词（可选）</label>
                <textarea className="input resize-none" rows={3}
                  value={form.system_prompt||''} onChange={e => set('system_prompt', e.target.value)}
                  placeholder="补充特定行业背景或回答规则..." />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-gray-800">私域引流</h3>
              <div className={`w-10 h-5 rounded-full cursor-pointer relative transition-colors ${pdEnabled ? 'bg-blue-500' : 'bg-gray-200'}`}
                onClick={() => setPdEnabled(!pdEnabled)}>
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${pdEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </div>
            </div>
            {pdEnabled && (
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">引导语</label>
                  <input className="input" placeholder="加我微信，获取专属优惠"
                    value={(form.private_domain_config as any)?.message||''}
                    onChange={e => setPd('message', e.target.value)} />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">二维码图片 URL</label>
                  <input className="input" placeholder="https://..."
                    value={(form.private_domain_config as any)?.qr_code_url||''}
                    onChange={e => setPd('qr_code_url', e.target.value)} />
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-4 mt-4 border-t border-gray-100">
              <div>
                <div className="text-sm font-medium text-gray-700">公开为 Demo</div>
                <div className="text-xs text-gray-400 mt-0.5">开启后此 Bot 将出现在 Demo 体验页供访客试用</div>
              </div>
              <div className={`w-10 h-5 rounded-full cursor-pointer relative transition-colors ${isDemo ? 'bg-blue-500' : 'bg-gray-200'}`}
                onClick={() => setIsDemo(!isDemo)}>
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${isDemo ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </div>
            </div>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}
          <div className="flex gap-3">
            <button className="btn-primary flex-1" onClick={save} disabled={saving}>
              {saving ? '保存中...' : saved ? '已保存 ✓' : '保存配置'}
            </button>
            <button className="btn-secondary" onClick={getEmbed}>嵌入代码</button>
          </div>
        </div>

        {/* 右侧：调试面板 */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
          style={{ height: '620px', display: 'flex', flexDirection: 'column' }}>

          {/* Header */}
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-medium text-gray-800">调试面板</span>
            <span className="text-xs text-gray-400">实时测试 Bot 效果</span>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-100">
            {DEBUG_TABS.map(tab => (
              <button key={tab} onClick={() => setDebugTab(tab)}
                className={`px-4 py-2 text-xs font-medium transition-colors border-b-2 -mb-px ${
                  debugTab === tab
                    ? 'text-gray-800 border-gray-800'
                    : 'text-gray-400 border-transparent hover:text-gray-600'
                }`}>{tab}</button>
            ))}
          </div>

          {/* 对话测试 Tab */}
          {debugTab === '对话测试' && (
            <>
              <div ref={msgsRef} className="flex-1 overflow-y-auto p-3 space-y-2 bg-gray-50">
                {messages.map((m, i) => (
                  <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                    {m.role === 'system' ? (
                      <div className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full self-center">{m.content}</div>
                    ) : (
                      <>
                        <div className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                          m.role === 'user'
                            ? 'bg-blue-600 text-white rounded-br-sm'
                            : 'bg-white text-gray-700 border border-gray-100 rounded-bl-sm'
                        }`}>
                          {m.content === '…' ? (
                            <span className="text-gray-400 animate-pulse">●●●</span>
                          ) : m.content}
                        </div>
                        {/* Debug 信息 */}
                        {m.debug && (
                          <div className="bg-white border border-gray-100 rounded-lg p-2 mt-1 max-w-[85%] text-xs space-y-1">
                            <div className="flex flex-wrap gap-1 items-center">
                              <span className={`px-1.5 py-0.5 rounded text-xs ${INTENT_COLOR[m.debug.intent] || 'bg-gray-100 text-gray-500'}`}>
                                {m.debug.intent}
                              </span>
                              {m.debug.intent_confidence != null && (
                                <span className="text-xs text-gray-400">
                                  {(m.debug.intent_confidence * 100).toFixed(0)}%
                                </span>
                              )}
                              {m.debug.intent_reason && (
                                <span className="text-xs text-gray-300 cursor-help" title={m.debug.intent_reason}>i</span>
                              )}
                              {m.cache_hit && (
                                <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 text-xs">缓存命中</span>
                              )}
                              <span className="text-gray-400 ml-auto">{m.latency_ms}ms</span>
                            </div>
                            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-xs">
                              <div className="flex justify-between">
                                <span className="text-gray-400">策略</span>
                                <span className="font-mono text-gray-600">{m.debug.transform_strategy||'—'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Grader</span>
                                <span className={`font-mono font-medium ${m.debug.grader_score >= 0.6 ? 'text-green-600' : 'text-amber-600'}`}>
                                  {m.debug.grader_score.toFixed(2)}
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">重试</span>
                                <span className="font-mono text-gray-600">{m.debug.attempts}次</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-400">Hallucination</span>
                                <span className={`font-mono ${m.debug.hallucination === 'pass' ? 'text-green-600' : 'text-red-500'}`}>
                                  {m.debug.hallucination}
                                </span>
                              </div>
                            </div>
                            {m.debug.chunks.length > 0 && (
                              <div className="pt-1 border-t border-gray-50">
                                <span className="text-gray-400">命中 chunks：</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {m.debug.chunks.map(c => (
                                    <span key={c.index}
                                      className="inline-block bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5 text-xs text-gray-500 cursor-pointer hover:bg-gray-100"
                                      title={c.preview}>
                                      #{c.index} {c.source === 'faq' ? 'FAQ' : `p${c.page}`} {c.score.toFixed(2)}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
              <div className="p-2 border-t border-gray-100 flex gap-2 bg-white">
                <input
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-xs outline-none focus:border-blue-400"
                  placeholder="输入消息测试..."
                  value={inputVal}
                  onChange={e => setInputVal(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendDebugMsg()}
                  disabled={sending}
                />
                <button
                  onClick={sendDebugMsg}
                  disabled={sending || !inputVal.trim()}
                  className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs disabled:opacity-40"
                >
                  {sending ? '…' : '发送'}
                </button>
              </div>
            </>
          )}

          {/* RAG 详情 Tab */}
          {debugTab === 'RAG 详情' && (
            <div className="flex-1 overflow-y-auto p-4">
              {!lastDebug ? (
                <p className="text-gray-400 text-xs text-center py-8">先在「对话测试」发送一条消息</p>
              ) : (
                <div className="space-y-3 text-xs">
                  <div className="bg-gray-50 rounded-lg p-3">
                    <p className="text-gray-500 mb-2 font-medium">Pipeline 执行结果</p>
                    <div className="space-y-1.5">
                      {[
                        ['意图分类', lastDebug.intent],
                        ['检索策略', lastDebug.transform_strategy || '—'],
                        ['re-retrieve 次数', `${lastDebug.attempts}`],
                        ['Grader 分数', `${lastDebug.grader_score.toFixed(3)} (阈值 ${lastDebug.grader_threshold})`],
                        ['Grounded', lastDebug.is_grounded ? '✓ 是' : '✗ 否'],
                        ['Hallucination', lastDebug.hallucination],
                        ['转人工', lastDebug.should_transfer ? '是' : '否'],
                      ].map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-gray-400">{k}</span>
                          <span className="font-mono text-gray-700">{v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  {lastDebug.chunks.length > 0 && (
                    <div>
                      <p className="text-gray-500 mb-2 font-medium">检索到的 Chunks（Top {lastDebug.chunks.length}）</p>
                      <div className="space-y-2">
                        {lastDebug.chunks.map(c => (
                          <div key={c.index} className="bg-gray-50 rounded-lg p-2.5">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded text-xs">#{c.index}</span>
                              <span className="text-gray-400">{c.source === 'faq' ? 'FAQ' : `第 ${c.page+1} 页`}</span>
                              <span className={`ml-auto font-mono ${c.score >= 0.6 ? 'text-green-600' : 'text-amber-600'}`}>
                                {c.score.toFixed(3)}
                              </span>
                            </div>
                            <p className="text-gray-600 leading-relaxed">{c.preview}...</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {lastDebug.pipeline_trace && lastDebug.pipeline_trace.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
                                   letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 8 }}>
                        节点执行链路
                      </p>
                      <div style={{ position: 'relative', paddingLeft: 20 }}>
                        <div style={{ position: 'absolute', left: 7, top: 8, bottom: 8,
                                      width: 1, background: 'var(--border)' }} />
                        {lastDebug.pipeline_trace.map((t: any, i: number) => (
                          <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10, position: 'relative' }}>
                            <div style={{
                              width: 15, height: 15, borderRadius: '50%', flexShrink: 0, marginTop: 2,
                              background: (t.node === 'grader' && !t.passed) || (t.node === 'retriever' && t.chunks_count === 0) ? '#FEF2F2' : '#ECFDF5',
                              border: `2px solid ${(t.node === 'grader' && !t.passed) || (t.node === 'retriever' && t.chunks_count === 0) ? '#FCA5A5' : '#6EE7B7'}`,
                            }} />
                            <div style={{ flex: 1, background: '#F9FAFB', borderRadius: 6, padding: '6px 10px' }}>
                              <div style={{ fontSize: 11, fontWeight: 600, color: '#374151', marginBottom: 3 }}>
                                {t.node}
                              </div>
                              <div style={{ fontSize: 11, color: '#6B7280', lineHeight: 1.5 }}>
                                {t.node === 'router' && `意图: ${t.intent}${t.skip_retrieval ? ' · 跳过检索' : ''}`}
                                {t.node === 'query_transform' && (
                                  <>
                                    <div>策略: {t.strategy}</div>
                                    {t.transformed !== t.original && <div style={{color:'#3B82F6'}}>转换: {t.transformed}</div>}
                                  </>
                                )}
                                {t.node === 'retriever' && (
                                  <span style={{ color: t.chunks_count === 0 ? '#DC2626' : '#059669', fontWeight: 500 }}>
                                    命中 {t.chunks_count} 个 chunks
                                    {t.chunks_count > 0 && ` · top ${typeof t.top_score === 'number' ? t.top_score.toFixed(3) : t.top_score}`}
                                  </span>
                                )}
                                {t.node === 'grader' && `分数 ${typeof t.score === 'number' ? t.score.toFixed(3) : t.score} · 重试 ${t.attempts} 次`}
                                {t.node === 'hallucination_checker' && `结果: ${t.action}`}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {lastDebug.transformed_query && (
                    <div style={{ marginTop: 12, padding: '8px 12px', background: '#EFF6FF',
                                  borderRadius: 6, fontSize: 11, color: '#1D4ED8' }}>
                      <span style={{ fontWeight: 600 }}>转换后查询：</span>{lastDebug.transformed_query}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* 历史记录 Tab */}
          {debugTab === '历史记录' && (
            <div className="flex-1 overflow-y-auto p-4">
              {messages.filter(m => m.role !== 'system').length === 0 ? (
                <p className="text-gray-400 text-xs text-center py-8">暂无测试记录</p>
              ) : (
                <div className="space-y-2 text-xs">
                  {messages.filter(m => m.role !== 'system').map((m, i) => (
                    <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
                      <span className={`px-2 py-0.5 rounded text-xs flex-shrink-0 ${
                        m.role === 'user' ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-500'
                      }`}>{m.role === 'user' ? '我' : 'Bot'}</span>
                      <span className="text-gray-700 leading-relaxed">{m.content}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 嵌入代码 Modal */}
      {showEmbed && (
        <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,.45)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9999}}
          onClick={() => setShowEmbed(false)}>
          <div className="bg-white rounded-xl p-6 w-[520px] max-w-[90vw]" onClick={e => e.stopPropagation()}>
            <p className="font-semibold text-gray-800 mb-2">嵌入代码</p>
            <p className="text-xs text-gray-500 mb-3">粘贴到您网站的 &lt;body&gt; 末尾：</p>
            <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto text-gray-700 leading-relaxed">{embedCode}</pre>
            <div className="flex gap-3 mt-4">
              <button className="btn-primary flex-1" onClick={() => {
                navigator.clipboard.writeText(embedCode)
                setCopied(true); setTimeout(() => setCopied(false), 2000)
              }}>{copied ? '已复制 ✓' : '复制代码'}</button>
              <button className="btn-secondary" onClick={() => setShowEmbed(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
