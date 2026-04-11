import { useEffect, useRef, useState } from 'react'
import api from '../api/client'

interface Bot {
  id: string
  name: string
}

interface Source {
  id: string
  name: string
  type: string
  status: string
  chunk_count: number
  error_msg?: string
  created_at: string
}

interface FAQ {
  id: string
  question: string
  answer: string
  priority: number
  is_active: boolean
  created_at: string
}

type Tab = 'docs' | 'faq'

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-500',
  processing: 'bg-blue-50 text-blue-600 animate-pulse',
  ready: 'bg-green-50 text-green-600',
  failed: 'bg-red-50 text-red-500',
}
const STATUS_LABEL: Record<string, string> = {
  pending: '待处理',
  processing: '处理中',
  ready: '已就绪',
  failed: '失败',
}

export default function Knowledge() {
  const [bots, setBots] = useState<Bot[]>([])
  const [botId, setBotId] = useState('')
  const [tab, setTab] = useState<Tab>('docs')

  // Docs
  const [sources, setSources] = useState<Source[]>([])
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  // FAQ
  const [faqs, setFaqs] = useState<FAQ[]>([])
  const [faqQ, setFaqQ] = useState('')
  const [faqA, setFaqA] = useState('')
  const [faqPri, setFaqPri] = useState(0)
  const [addingFaq, setAddingFaq] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [editQ, setEditQ] = useState('')
  const [editA, setEditA] = useState('')

  useEffect(() => {
    api.get('/bots').then((r) => {
      const b: Bot[] = r.data.data
      setBots(b)
      if (b.length > 0 && !botId) setBotId(b[0].id)
    })
  }, [])

  const loadDocs = () => {
    if (!botId) return Promise.resolve()
    return api
      .get(`/bots/${botId}/knowledge`)
      .then((r) => setSources(r.data.data))
      .catch(() => {})
  }
  const loadFaqs = () => {
    if (!botId) return Promise.resolve()
    return api
      .get(`/bots/${botId}/faq`)
      .then((r) => setFaqs(r.data.data))
      .catch(() => {})
  }

  useEffect(() => {
    if (!botId) return
    loadDocs()
    loadFaqs()
  }, [botId])

  // 自动轮询 pending/processing 状态
  useEffect(() => {
    if (!botId) return
    const hasPending = sources.some(
      (s) => s.status === 'pending' || s.status === 'processing',
    )
    if (!hasPending) return
    const t = setInterval(() => loadDocs(), 5000)
    return () => clearInterval(t)
  }, [botId, sources])

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !botId) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      await api.post(`/bots/${botId}/knowledge`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await loadDocs()
    } catch (e: any) {
      alert(e.response?.data?.reason || '上传失败')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const delDoc = async (id: string) => {
    if (!confirm('确认删除此知识源？相关 chunks 将从向量库清除。')) return
    await api.delete(`/bots/${botId}/knowledge/${id}`)
    setSources((s) => s.filter((x) => x.id !== id))
  }

  const addFaq = async () => {
    if (!faqQ.trim() || !faqA.trim()) return
    setAddingFaq(true)
    try {
      await api.post(`/bots/${botId}/faq`, {
        question: faqQ.trim(),
        answer: faqA.trim(),
        priority: faqPri,
      })
      setFaqQ('')
      setFaqA('')
      setFaqPri(0)
      await loadFaqs()
    } catch (e: any) {
      alert(e.response?.data?.reason || '添加失败')
    } finally {
      setAddingFaq(false)
    }
  }

  const delFaq = async (id: string) => {
    if (!confirm('确认删除此 FAQ？')) return
    try {
      await api.delete(`/bots/${botId}/faq/${id}`)
      setFaqs((f) => f.filter((x) => x.id !== id))
    } catch (e: any) {
      alert(e.response?.data?.reason || '删除失败')
    }
  }

  const saveEditFaq = async (id: string) => {
    try {
      await api.put(`/bots/${botId}/faq/${id}`, {
        question: editQ,
        answer: editA,
      })
      setEditId(null)
      await loadFaqs()
    } catch (e: any) {
      alert(e.response?.data?.reason || '保存失败')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">知识库管理</h2>
        <select
          className="input w-44"
          value={botId}
          onChange={(e) => setBotId(e.target.value)}
        >
          {bots.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-1 mb-5 bg-gray-100 rounded-lg p-1 w-fit">
        {(['docs', 'faq'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-white text-gray-800 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'docs' ? `文档 (${sources.length})` : `FAQ (${faqs.length})`}
          </button>
        ))}
      </div>

      {tab === 'docs' && (
        <div>
          <div className="flex gap-3 mb-4 items-center">
            <label
              className={`btn-primary cursor-pointer ${
                !botId || uploading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {uploading ? '上传中...' : '上传文档'}
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".pdf,.xlsx,.xls,.docx,.doc"
                onChange={upload}
                disabled={!botId || uploading}
              />
            </label>
            <span className="text-xs text-gray-400">
              PDF / Excel / Word，最大 20MB
            </span>
          </div>
          <div className="space-y-2">
            {sources.map((src) => (
              <div
                key={src.id}
                className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {src.name}
                  </p>
                  {src.error_msg && (
                    <p className="text-xs text-red-400 mt-0.5">
                      {src.error_msg}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(src.created_at).toLocaleString('zh')}
                    {src.chunk_count > 0 && ` · ${src.chunk_count} chunks`}
                  </p>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded-full flex-shrink-0 ${
                    STATUS_STYLE[src.status] || ''
                  }`}
                >
                  {STATUS_LABEL[src.status] || src.status}
                </span>
                <button
                  className="text-xs text-red-400 hover:underline flex-shrink-0"
                  onClick={() => delDoc(src.id)}
                >
                  删除
                </button>
              </div>
            ))}
            {sources.length === 0 && (
              <p className="text-gray-400 text-sm py-8 text-center">
                暂无文档，请上传
              </p>
            )}
          </div>
        </div>
      )}

      {tab === 'faq' && (
        <div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-4">
            <p className="text-sm font-medium text-gray-700 mb-3">添加 FAQ</p>
            <div className="space-y-2">
              <input
                className="input"
                placeholder="问题（如：你们的 MOQ 是多少？）"
                value={faqQ}
                onChange={(e) => setFaqQ(e.target.value)}
              />
              <textarea
                className="input resize-none"
                rows={2}
                placeholder="答案"
                value={faqA}
                onChange={(e) => setFaqA(e.target.value)}
              />
              <div className="flex gap-2 items-center">
                <label className="text-xs text-gray-500">优先级</label>
                <input
                  type="number"
                  className="input w-20 text-sm"
                  value={faqPri}
                  min={0}
                  max={100}
                  onChange={(e) => setFaqPri(parseInt(e.target.value) || 0)}
                />
                <span className="text-xs text-gray-400 flex-1">
                  数字越大优先级越高（0-100）
                </span>
                <button
                  className="btn-primary px-4"
                  onClick={addFaq}
                  disabled={addingFaq || !faqQ.trim() || !faqA.trim()}
                >
                  {addingFaq ? '添加中...' : '+ 添加'}
                </button>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            {faqs.map((faq) => (
              <div
                key={faq.id}
                className="bg-white rounded-xl p-4 shadow-sm border border-gray-100"
              >
                {editId === faq.id ? (
                  <div className="space-y-2">
                    <input
                      className="input text-sm"
                      value={editQ}
                      onChange={(e) => setEditQ(e.target.value)}
                    />
                    <textarea
                      className="input resize-none text-sm"
                      rows={2}
                      value={editA}
                      onChange={(e) => setEditA(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <button
                        className="btn-primary text-xs px-3 py-1"
                        onClick={() => saveEditFaq(faq.id)}
                      >
                        保存
                      </button>
                      <button
                        className="btn-secondary text-xs px-3 py-1"
                        onClick={() => setEditId(null)}
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-3 items-start">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800">
                        {faq.question}
                      </p>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {faq.answer}
                      </p>
                    </div>
                    {faq.priority > 0 && (
                      <span className="text-xs bg-amber-50 text-amber-600 px-1.5 py-0.5 rounded flex-shrink-0">
                        P{faq.priority}
                      </span>
                    )}
                    <div className="flex gap-2 flex-shrink-0">
                      <button
                        className="text-xs text-blue-500 hover:underline"
                        onClick={() => {
                          setEditId(faq.id)
                          setEditQ(faq.question)
                          setEditA(faq.answer)
                        }}
                      >
                        编辑
                      </button>
                      <button
                        className="text-xs text-red-400 hover:underline"
                        onClick={() => delFaq(faq.id)}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {faqs.length === 0 && (
              <p className="text-gray-400 text-sm py-8 text-center">
                暂无 FAQ，请添加
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
