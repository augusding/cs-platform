import { useEffect, useState } from 'react'
import api from '../api/client'

interface Bot {
  id: string
  name: string
  language: string
  status: string
  bot_api_key_preview: string
  welcome_message: string
  created_at: string
}

const LANG_LABEL: Record<string, string> = {
  zh: '中文',
  en: 'English',
  both: '双语',
}

export default function Bots() {
  const [bots, setBots] = useState<Bot[]>([])
  const [name, setName] = useState('')
  const [lang, setLang] = useState('zh')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [embedBot, setEmbedBot] = useState<{ id: string; code: string } | null>(null)
  const [loadingEmbed, setLoadingEmbed] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const load = () =>
    api
      .get('/bots')
      .then((r) => setBots(r.data.data))
      .catch(() => {})

  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    if (!name.trim()) {
      setError('请输入 Bot 名称')
      return
    }
    setCreating(true)
    setError('')
    try {
      await api.post('/bots', { name: name.trim(), language: lang })
      setName('')
      await load()
    } catch (e: any) {
      setError(e.response?.data?.reason || '创建失败，请重试')
    } finally {
      setCreating(false)
    }
  }

  const del = async (id: string, botName: string) => {
    if (!confirm(`确认删除 Bot「${botName}」？此操作不可撤销。`)) return
    try {
      await api.delete(`/bots/${id}`)
      await load()
    } catch (e: any) {
      alert(e.response?.data?.reason || '删除失败')
    }
  }

  const getEmbedCode = async (botId: string) => {
    setLoadingEmbed(botId)
    try {
      const { data } = await api.post(`/bots/${botId}/reveal-key`)
      setEmbedBot({ id: botId, code: data.data.embed_code })
    } catch (e: any) {
      alert(e.response?.data?.reason || '获取嵌入代码失败')
    } finally {
      setLoadingEmbed(null)
    }
  }

  const copyCode = () => {
    if (!embedBot) return
    navigator.clipboard.writeText(embedBot.code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Bot 管理</h2>

      {/* 创建表单 */}
      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-6">
        <p className="text-sm font-medium text-gray-700 mb-3">创建新 Bot</p>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs text-gray-500 mb-1 block">Bot 名称 *</label>
            <input
              className="input"
              placeholder="例：外贸客服 Bot"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                setError('')
              }}
              onKeyDown={(e) => e.key === 'Enter' && create()}
            />
          </div>
          <div className="w-32">
            <label className="text-xs text-gray-500 mb-1 block">语言</label>
            <select
              className="input"
              value={lang}
              onChange={(e) => setLang(e.target.value)}
            >
              <option value="zh">中文</option>
              <option value="en">English</option>
              <option value="both">双语</option>
            </select>
          </div>
          <button
            className="btn-primary h-9 px-5"
            onClick={create}
            disabled={creating}
          >
            {creating ? '创建中...' : '+ 创建'}
          </button>
        </div>
        {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
      </div>

      {/* 嵌入代码弹窗 */}
      {embedBot && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{ background: 'rgba(0,0,0,0.45)' }}
          onClick={() => setEmbedBot(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-semibold text-gray-800 mb-3">嵌入代码</p>
            <p className="text-xs text-gray-500 mb-3">
              将以下代码粘贴到您网站的 &lt;body&gt; 标签末尾：
            </p>
            <pre className="bg-gray-50 text-gray-800 rounded-lg p-3 text-xs leading-relaxed overflow-x-auto border border-gray-100">
              {embedBot.code}
            </pre>
            <div className="flex gap-3 mt-4">
              <button className="btn-primary flex-1" onClick={copyCode}>
                {copied ? '已复制 ✓' : '复制代码'}
              </button>
              <button className="btn-secondary" onClick={() => setEmbedBot(null)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bot 列表 */}
      <div className="space-y-3">
        {bots.map((bot) => (
          <div
            key={bot.id}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
          >
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold flex-shrink-0 text-lg">
                {bot.name[0]}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800">{bot.name}</p>
                <p className="text-sm text-gray-400 mt-0.5">
                  {LANG_LABEL[bot.language] || bot.language} ·{' '}
                  {bot.bot_api_key_preview}
                </p>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full flex-shrink-0 ${
                  bot.status === 'active'
                    ? 'bg-green-50 text-green-600'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {bot.status === 'active' ? '运行中' : '已停用'}
              </span>
              <div className="flex gap-3 flex-shrink-0">
                <button
                  className="text-sm text-blue-600 hover:underline disabled:opacity-50"
                  onClick={() => getEmbedCode(bot.id)}
                  disabled={loadingEmbed === bot.id}
                >
                  {loadingEmbed === bot.id ? '获取中...' : '嵌入代码'}
                </button>
                <a
                  className="text-sm text-gray-500 hover:underline"
                  href={`/chat/${bot.id}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  预览
                </a>
                <button
                  className="text-sm text-red-400 hover:underline"
                  onClick={() => del(bot.id, bot.name)}
                >
                  删除
                </button>
              </div>
            </div>
          </div>
        ))}
        {bots.length === 0 && (
          <div className="bg-white rounded-xl p-10 shadow-sm border border-gray-100 text-center">
            <p className="text-gray-400 text-sm">暂无 Bot，请先创建</p>
          </div>
        )}
      </div>
    </div>
  )
}
