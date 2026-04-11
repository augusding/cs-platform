import { useEffect, useState, useRef } from 'react'
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
  created_at: string
  error_msg?: string
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-500',
  processing: 'bg-blue-50 text-blue-600',
  ready: 'bg-green-50 text-green-600',
  failed: 'bg-red-50 text-red-500',
}

export default function Knowledge() {
  const [bots, setBots] = useState<Bot[]>([])
  const [botId, setBotId] = useState('')
  const [sources, setSources] = useState<Source[]>([])
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.get('/bots').then((r) => {
      const b = r.data.data as Bot[]
      setBots(b)
      if (b.length > 0) setBotId(b[0].id)
    })
  }, [])

  useEffect(() => {
    if (botId) api.get(`/bots/${botId}/knowledge`).then((r) => setSources(r.data.data))
  }, [botId])

  // 自动轮询：有 pending/processing 时每 5s 刷新
  useEffect(() => {
    if (!botId) return
    const hasPending = sources.some(
      (s) => s.status === 'pending' || s.status === 'processing',
    )
    if (!hasPending) return
    const timer = setInterval(() => {
      api
        .get(`/bots/${botId}/knowledge`)
        .then((r) => setSources(r.data.data))
        .catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [botId, sources])

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      await api.post(`/bots/${botId}/knowledge`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      // 上传后立即刷新，之后由 polling effect 接管
      const r = await api.get(`/bots/${botId}/knowledge`)
      setSources(r.data.data)
    } catch (e: any) {
      alert(e.response?.data?.reason || '上传失败')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const del = async (id: string) => {
    if (!confirm('确认删除？')) return
    await api.delete(`/bots/${botId}/knowledge/${id}`)
    setSources((s) => s.filter((x) => x.id !== id))
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">知识库管理</h2>

      <div className="flex gap-3 mb-6 items-center">
        <select
          className="input w-48"
          value={botId}
          onChange={(e) => setBotId(e.target.value)}
        >
          {bots.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <label
          className={`btn-primary cursor-pointer ${
            uploading || !botId ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {uploading ? '上传中...' : '上传文档'}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.xlsx,.xls,.docx,.doc"
            className="hidden"
            onChange={upload}
            disabled={uploading || !botId}
          />
        </label>
        <span className="text-sm text-gray-400">支持 PDF / Excel / Word，最大 20MB</span>
      </div>

      <div className="space-y-2">
        {sources.map((src) => (
          <div
            key={src.id}
            className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 flex items-center gap-4"
          >
            <div className="flex-1">
              <p className="font-medium text-gray-800 text-sm">{src.name}</p>
              {src.error_msg && (
                <p className="text-xs text-red-400 mt-0.5">{src.error_msg}</p>
              )}
            </div>
            <span className="text-xs text-gray-400">
              {src.chunk_count > 0 ? `${src.chunk_count} chunks` : ''}
            </span>
            <span
              className={`text-xs px-2 py-1 rounded-full ${STATUS_STYLE[src.status] || ''}`}
            >
              {src.status}
            </span>
            <button
              className="text-sm text-red-400 hover:underline"
              onClick={() => del(src.id)}
            >
              删除
            </button>
          </div>
        ))}
        {sources.length === 0 && (
          <p className="text-gray-400 text-sm text-center py-8">
            暂无知识来源，请先上传文档
          </p>
        )}
      </div>
    </div>
  )
}
