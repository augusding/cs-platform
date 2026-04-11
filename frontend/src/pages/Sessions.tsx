import { useEffect, useState } from 'react'
import api from '../api/client'

interface Session {
  id: string
  bot_id: string
  visitor_id: string
  language: string
  status: string
  message_count: number
  started_at: string
}

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const load = (p: number) => {
    api
      .get(`/admin/sessions?page=${p}&page_size=20`)
      .then((r) => {
        setSessions(r.data.data)
        setTotal(r.data.meta?.total ?? 0)
      })
      .catch(() => setSessions([]))
  }

  useEffect(() => {
    load(page)
  }, [page])

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">
        会话记录{' '}
        <span className="text-base text-gray-400 font-normal">共 {total} 条</span>
      </h2>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              {['会话ID', '访客ID', '语言', '消息数', '状态', '开始时间'].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sessions.map((s, i) => (
              <tr key={s.id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">
                  {s.id.slice(0, 8)}...
                </td>
                <td className="px-4 py-3 text-gray-600">{s.visitor_id.slice(0, 12)}</td>
                <td className="px-4 py-3">{s.language === 'zh' ? '中文' : 'EN'}</td>
                <td className="px-4 py-3 text-center">{s.message_count}</td>
                <td className="px-4 py-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      s.status === 'active'
                        ? 'bg-green-50 text-green-600'
                        : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {new Date(s.started_at).toLocaleString('zh')}
                </td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  暂无会话记录
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            className="btn-secondary"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            上一页
          </button>
          <span className="text-sm text-gray-500 py-2">第 {page} 页</span>
          <button
            className="btn-secondary"
            disabled={page * 20 >= total}
            onClick={() => setPage((p) => p + 1)}
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
