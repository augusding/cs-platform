import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'

interface Message {
  id: string
  role: string
  content: string
  grader_score?: number | null
  is_grounded?: boolean | null
  created_at: string
}

interface Session {
  id: string
  bot_name: string
  visitor_id: string
  language: string
  status: string
  message_count: number
  started_at: string
  ended_at?: string
  messages: Message[]
}

const ROLE_STYLE: Record<string, string> = {
  user: 'bg-blue-500 text-white',
  assistant: 'bg-gray-100 text-gray-800',
  human_agent: 'bg-green-100 text-green-800',
}

const ROLE_LABEL: Record<string, string> = {
  user: '访客',
  assistant: 'AI',
  human_agent: '人工客服',
}

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [session, setSession] = useState<Session | null>(null)
  const [transferring, setTransferring] = useState(false)

  useEffect(() => {
    if (!sessionId) return
    api
      .get(`/admin/sessions/${sessionId}`)
      .then((r) => setSession(r.data.data))
      .catch(() => {})
  }, [sessionId])

  const transfer = async () => {
    if (!confirm('确认接管此会话？接管后 AI 将停止自动回复。')) return
    setTransferring(true)
    try {
      await api.post(`/admin/sessions/${sessionId}/transfer`)
      setSession((s) => (s ? { ...s, status: 'transferred' } : s))
    } catch (e: any) {
      alert(e.response?.data?.reason || '接管失败')
    } finally {
      setTransferring(false)
    }
  }

  if (!session) return <div className="text-gray-400 text-sm p-8">加载中...</div>

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => navigate('/sessions')}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← 会话列表
        </button>
        <span className="text-gray-300">/</span>
        <span className="text-sm text-gray-600 font-mono">
          {sessionId?.slice(0, 8)}...
        </span>
      </div>

      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="font-medium text-gray-800">{session.bot_name}</p>
            <p className="text-sm text-gray-400 mt-1">
              访客：{session.visitor_id.slice(0, 12)} ·{' '}
              {session.language === 'zh' ? '中文' : 'EN'} · {session.message_count} 条消息
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              {new Date(session.started_at).toLocaleString('zh')}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                session.status === 'active'
                  ? 'bg-green-50 text-green-600'
                  : session.status === 'transferred'
                  ? 'bg-amber-50 text-amber-600'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {session.status === 'active'
                ? '进行中'
                : session.status === 'transferred'
                ? '已接管'
                : '已结束'}
            </span>
            {session.status === 'active' && (
              <button
                className="btn-primary text-xs px-3 py-1.5"
                onClick={transfer}
                disabled={transferring}
              >
                {transferring ? '接管中...' : '接管会话'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <p className="text-sm font-medium text-gray-700 mb-4">消息记录</p>
        <div className="flex flex-col gap-3 max-h-[500px] overflow-y-auto">
          {session.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.role === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-xs text-gray-400">
                  {ROLE_LABEL[msg.role] || msg.role}
                </span>
                <span className="text-xs text-gray-300">
                  {new Date(msg.created_at).toLocaleTimeString('zh')}
                </span>
                {msg.grader_score != null && (
                  <span
                    className={`text-xs px-1 rounded ${
                      msg.grader_score >= 0.6
                        ? 'bg-green-50 text-green-500'
                        : 'bg-red-50 text-red-400'
                    }`}
                  >
                    {(msg.grader_score * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              <div
                className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed whitespace-pre-wrap ${
                  ROLE_STYLE[msg.role] || 'bg-gray-100 text-gray-800'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {session.messages.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-4">暂无消息</p>
          )}
        </div>
      </div>
    </div>
  )
}
