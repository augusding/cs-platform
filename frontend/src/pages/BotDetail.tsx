import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

interface BotStats {
  chunk_total: number
  faq_count: number
}

interface BotConfig {
  id: string
  name: string
  welcome_message: string
  language: string
  style: string
  system_prompt: string
  avatar_url: string
  lead_capture_fields: any[]
  private_domain_config: any
  stats?: BotStats
}

interface FormShape {
  name: string
  welcome_message: string
  language: string
  style: string
  system_prompt: string
  avatar_url: string
  private_domain_config: { message?: string; qr_code_url?: string; enabled?: boolean }
}

const STYLE_OPTIONS = [
  { value: 'friendly', label: '友好亲切' },
  { value: 'formal', label: '正式专业' },
  { value: 'professional', label: '简洁高效' },
]

export default function BotDetail() {
  const { botId } = useParams<{ botId: string }>()
  const navigate = useNavigate()

  const [bot, setBot] = useState<BotConfig | null>(null)
  const [form, setForm] = useState<FormShape>({
    name: '',
    welcome_message: '',
    language: 'zh',
    style: 'friendly',
    system_prompt: '',
    avatar_url: '',
    private_domain_config: {},
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [embedCode, setEmbedCode] = useState('')
  const [showEmbed, setShowEmbed] = useState(false)
  const [copied, setCopied] = useState(false)
  const [pdEnabled, setPdEnabled] = useState(false)

  useEffect(() => {
    if (!botId) return
    api.get(`/bots/${botId}/detail`).then((r) => {
      const b: BotConfig = r.data.data
      // 后端 lead_capture_fields / private_domain_config 可能是 JSON 字符串
      let pdc: any = b.private_domain_config
      if (typeof pdc === 'string') {
        try {
          pdc = JSON.parse(pdc)
        } catch {
          pdc = {}
        }
      }
      setBot(b)
      setForm({
        name: b.name,
        welcome_message: b.welcome_message || '',
        language: b.language,
        style: b.style,
        system_prompt: b.system_prompt || '',
        avatar_url: b.avatar_url || '',
        private_domain_config: pdc || {},
      })
      setPdEnabled(!!(pdc && pdc.enabled))
    })
  }, [botId])

  const save = async () => {
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const payload: any = { ...form }
      if (pdEnabled) {
        payload.private_domain_config = {
          ...(form.private_domain_config || {}),
          enabled: true,
        }
      } else {
        payload.private_domain_config = null
      }
      await api.put(`/bots/${botId}`, payload)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: any) {
      setError(e.response?.data?.reason || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const getEmbed = async () => {
    try {
      const { data } = await api.post(`/bots/${botId}/reveal-key`)
      setEmbedCode(data.data.embed_code)
      setShowEmbed(true)
    } catch (e: any) {
      alert(e.response?.data?.reason || '获取失败')
    }
  }

  const set = <K extends keyof FormShape>(k: K, v: FormShape[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const setPd = (k: string, v: any) =>
    setForm((f) => ({
      ...f,
      private_domain_config: { ...(f.private_domain_config || {}), [k]: v },
    }))

  if (!bot) return <div className="text-gray-400 text-sm p-8">加载中...</div>

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => navigate('/bots')}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Bot 列表
        </button>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-medium text-gray-800">{bot.name}</span>
      </div>

      {bot.stats && (
        <div className="grid grid-cols-2 gap-3 mb-6">
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
            <p className="text-2xl font-semibold text-blue-600">
              {bot.stats.chunk_total}
            </p>
            <p className="text-xs text-gray-400 mt-1">知识库 Chunks</p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm text-center">
            <p className="text-2xl font-semibold text-green-600">
              {bot.stats.faq_count}
            </p>
            <p className="text-xs text-gray-400 mt-1">FAQ 条目</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-4">
        <h3 className="font-medium text-gray-800 mb-4">基础配置</h3>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Bot 名称 *</label>
            <input
              className="input"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">欢迎语</label>
            <input
              className="input"
              value={form.welcome_message}
              onChange={(e) => set('welcome_message', e.target.value)}
              placeholder="您好，有什么可以帮您？"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">语言</label>
              <select
                className="input"
                value={form.language}
                onChange={(e) => set('language', e.target.value)}
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
                <option value="both">双语</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">对话风格</label>
              <select
                className="input"
                value={form.style}
                onChange={(e) => set('style', e.target.value)}
              >
                {STYLE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              头像 URL（可选）
            </label>
            <input
              className="input"
              value={form.avatar_url}
              onChange={(e) => set('avatar_url', e.target.value)}
              placeholder="https://..."
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              自定义系统提示词（可选，高级设置）
            </label>
            <textarea
              className="input resize-none"
              rows={3}
              value={form.system_prompt}
              onChange={(e) => set('system_prompt', e.target.value)}
              placeholder="补充特定行业背景或回答规则..."
            />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium text-gray-800">私域引流</h3>
          <label className="flex items-center gap-2 cursor-pointer">
            <div
              className={`w-10 h-5 rounded-full transition-colors relative ${
                pdEnabled ? 'bg-blue-500' : 'bg-gray-200'
              }`}
              onClick={() => setPdEnabled(!pdEnabled)}
            >
              <div
                className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                  pdEnabled ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </div>
            <span className="text-sm text-gray-500">
              {pdEnabled ? '已开启' : '已关闭'}
            </span>
          </label>
        </div>
        {pdEnabled && (
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">引导语</label>
              <input
                className="input"
                placeholder="加我微信，获取专属优惠"
                value={form.private_domain_config?.message || ''}
                onChange={(e) => setPd('message', e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">
                二维码图片 URL
              </label>
              <input
                className="input"
                placeholder="https://..."
                value={form.private_domain_config?.qr_code_url || ''}
                onChange={(e) => setPd('qr_code_url', e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
      <div className="flex gap-3">
        <button
          className="btn-primary flex-1"
          onClick={save}
          disabled={saving}
        >
          {saving ? '保存中...' : saved ? '已保存 ✓' : '保存配置'}
        </button>
        <button className="btn-secondary" onClick={getEmbed}>
          获取嵌入代码
        </button>
      </div>

      {showEmbed && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{ background: 'rgba(0,0,0,0.45)' }}
          onClick={() => setShowEmbed(false)}
        >
          <div
            className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-semibold text-gray-800 mb-2">嵌入代码</p>
            <p className="text-xs text-gray-500 mb-3">
              粘贴到您网站的 &lt;body&gt; 末尾：
            </p>
            <pre className="bg-gray-50 rounded-lg p-3 text-xs overflow-x-auto text-gray-700 leading-relaxed border border-gray-100">
              {embedCode}
            </pre>
            <div className="flex gap-3 mt-4">
              <button
                className="btn-primary flex-1"
                onClick={() => {
                  navigator.clipboard.writeText(embedCode)
                  setCopied(true)
                  setTimeout(() => setCopied(false), 2000)
                }}
              >
                {copied ? '已复制 ✓' : '复制代码'}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowEmbed(false)}
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
