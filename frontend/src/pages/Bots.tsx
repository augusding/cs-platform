import { useEffect, useState } from 'react'
import api from '../api/client'

interface Bot {
  id: string
  name: string
  language: string
  status: string
  bot_api_key_preview: string
  created_at: string
}

export default function Bots() {
  const [bots, setBots] = useState<Bot[]>([])
  const [name, setName] = useState('')
  const [lang, setLang] = useState('zh')
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const load = () => api.get('/bots').then((r) => setBots(r.data.data))
  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    if (!name.trim()) return
    setCreating(true)
    try {
      await api.post('/bots', { name, language: lang })
      setName('')
      load()
    } catch (e: any) {
      alert(e.response?.data?.reason || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const del = async (id: string) => {
    if (!confirm('确认删除？')) return
    await api.delete(`/bots/${id}`)
    load()
  }

  const copyEmbed = (bot: Bot) => {
    const code =
      `<script>window.CS_CONFIG={botId:"${bot.id}"}</script>\n` +
      `<script src="${window.location.origin}/widget.js" async></script>`
    navigator.clipboard.writeText(code)
    setCopied(bot.id)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Bot 管理</h2>

      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-6 flex gap-3 items-end">
        <div className="flex-1">
          <label className="text-sm text-gray-500 mb-1 block">Bot 名称</label>
          <input
            className="input"
            placeholder="例：外贸客服Bot"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm text-gray-500 mb-1 block">语言</label>
          <select className="input" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>
        <button className="btn-primary" onClick={create} disabled={creating}>
          {creating ? '创建中...' : '+ 创建'}
        </button>
      </div>

      <div className="space-y-3">
        {bots.map((bot) => (
          <div
            key={bot.id}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex items-center gap-4"
          >
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold flex-shrink-0">
              {bot.name[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-800">{bot.name}</p>
              <p className="text-sm text-gray-400">
                {bot.bot_api_key_preview} · {bot.language}
              </p>
            </div>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                bot.status === 'active'
                  ? 'bg-green-50 text-green-600'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {bot.status === 'active' ? '运行中' : '已停用'}
            </span>
            <button
              className="text-sm text-blue-600 hover:underline"
              onClick={() => copyEmbed(bot)}
            >
              {copied === bot.id ? '已复制 ✓' : '复制嵌入代码'}
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
              onClick={() => del(bot.id)}
            >
              删除
            </button>
          </div>
        ))}
        {bots.length === 0 && (
          <p className="text-gray-400 text-sm text-center py-8">暂无 Bot，请先创建</p>
        )}
      </div>
    </div>
  )
}
