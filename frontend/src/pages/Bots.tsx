import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

interface Bot {
  id: string; name: string; language: string; status: string
  bot_api_key_preview: string; welcome_message: string; created_at: string
}
const LANG_LABEL: Record<string, string> = { zh: '中文', en: 'English', both: '双语' }

export default function Bots() {
  const navigate = useNavigate()
  const [bots, setBots]         = useState<Bot[]>([])
  const [name, setName]         = useState('')
  const [lang, setLang]         = useState('zh')
  const [creating, setCreating] = useState(false)
  const [error, setError]       = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [embedBot, setEmbedBot] = useState<{id:string; code:string}|null>(null)
  const [loadingEmbed, setLoadingEmbed] = useState<string|null>(null)
  const [copied, setCopied]     = useState(false)

  const load = () => api.get('/bots').then(r => setBots(r.data.data)).catch(() => {})
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name.trim()) { setError('请输入 Bot 名称'); return }
    setCreating(true); setError('')
    try {
      await api.post('/bots', { name: name.trim(), language: lang })
      setName(''); setShowCreate(false); await load()
    } catch (e: any) {
      setError(e.response?.data?.reason || e.userMessage || '创建失败')
    } finally { setCreating(false) }
  }

  const del = async (id: string, botName: string) => {
    if (!confirm(`确认删除 Bot「${botName}」？此操作不可撤销。`)) return
    try { await api.delete(`/bots/${id}`); await load() }
    catch (e: any) { alert(e.response?.data?.reason || '删除失败') }
  }

  const getEmbedCode = async (botId: string) => {
    setLoadingEmbed(botId)
    try {
      const { data } = await api.post(`/bots/${botId}/reveal-key`)
      setEmbedBot({ id: botId, code: data.data.embed_code })
    } catch (e: any) { alert(e.userMessage || '获取失败') }
    finally { setLoadingEmbed(null) }
  }

  return (
    <div>
      {showCreate && (
        <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,.4)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9999 }}
          onClick={() => setShowCreate(false)}>
          <div className="card" style={{ width: 440, padding: 24, borderRadius: 16 }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20 }}>新建 Bot</h3>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>Bot 名称 *</div>
              <input className="input" placeholder="例：外贸客服 Bot" value={name}
                onChange={e => { setName(e.target.value); setError('') }}
                onKeyDown={e => e.key === 'Enter' && create()}
                autoFocus />
            </div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>语言</div>
              <select className="input" value={lang} onChange={e => setLang(e.target.value)}>
                <option value="zh">中文</option>
                <option value="en">English</option>
                <option value="both">双语</option>
              </select>
            </div>
            {error && <p style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 12 }}>{error}</p>}
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={create} disabled={creating}>
                {creating ? '创建中...' : '确认创建'}
              </button>
              <button className="btn-secondary" onClick={() => setShowCreate(false)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {embedBot && (
        <div style={{ position:'fixed',inset:0,background:'rgba(0,0,0,.4)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9999 }}
          onClick={() => setEmbedBot(null)}>
          <div className="card" style={{ width: 520, maxWidth: '90vw', padding: 24, borderRadius: 16 }}
            onClick={e => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>嵌入代码</h3>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 14 }}>
              将以下代码粘贴到您网站 &lt;body&gt; 末尾：
            </p>
            <pre style={{
              background: '#F8F9FC', borderRadius: 8, padding: '12px 14px',
              fontSize: 12, overflowX: 'auto', color: 'var(--text-primary)', lineHeight: 1.6,
              border: '1px solid var(--border)', marginBottom: 16,
            }}>{embedBot.code}</pre>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn-primary" style={{ flex: 1 }} onClick={() => {
                navigator.clipboard.writeText(embedBot.code)
                setCopied(true); setTimeout(() => setCopied(false), 2000)
              }}>{copied ? '已复制 ✓' : '复制代码'}</button>
              <button className="btn-secondary" onClick={() => setEmbedBot(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>+ 新建 Bot</button>
      </div>

      {bots.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)' }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🤖</div>
          <p style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>还没有 Bot</p>
          <p style={{ fontSize: 13, marginBottom: 20 }}>创建第一个 Bot，开始接入智能客服</p>
          <button className="btn-primary" onClick={() => setShowCreate(true)}>+ 新建 Bot</button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16 }}>
          {bots.map(bot => (
            <div key={bot.id} className="card" style={{ overflow: 'visible' }}>
              <div style={{ padding: '18px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 10, background: 'var(--accent-light)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, flexShrink: 0,
                  }}>🤖</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>{bot.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                      {LANG_LABEL[bot.language]} · {bot.bot_api_key_preview}
                    </div>
                  </div>
                  <span className={`badge ${bot.status === 'active' ? 'badge-success' : 'badge-neutral'}`}>
                    {bot.status === 'active' ? '运行中' : '停用'}
                  </span>
                </div>
                <div style={{ marginTop: 16, display: 'flex', gap: 6 }}>
                  <button className="btn-secondary" style={{ flex: 1, height: 32, fontSize: 12 }}
                    onClick={() => navigate(`/bots/${bot.id}`)}>配置</button>
                  <button className="btn-ghost" style={{ height: 32, fontSize: 12 }}
                    onClick={() => window.open(`/chat/${bot.id}`, '_blank')}>预览</button>
                  <button className="btn-ghost" style={{ height: 32, fontSize: 12 }}
                    disabled={loadingEmbed === bot.id}
                    onClick={() => getEmbedCode(bot.id)}>
                    {loadingEmbed === bot.id ? '...' : '嵌入'}
                  </button>
                  <button className="btn-ghost" style={{ height: 32, fontSize: 12, color: 'var(--danger)' }}
                    onClick={() => del(bot.id, bot.name)}>删除</button>
                </div>
              </div>
            </div>
          ))}
          <div onClick={() => setShowCreate(true)} style={{
            border: '2px dashed var(--border)', borderRadius: 12, cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: 8, padding: '32px 20px', minHeight: 140,
            transition: 'border-color .15s', color: 'var(--text-muted)',
          }}
            onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.borderColor = '#93C5FD'}
            onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)'}
          >
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--border-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" /></svg>
            </div>
            <span style={{ fontSize: 14, fontWeight: 500 }}>新建 Bot</span>
          </div>
        </div>
      )}
    </div>
  )
}
