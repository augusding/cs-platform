import { useEffect, useState } from 'react'
import api from '../api/client'

interface Stats {
  total_sessions: number
  resolved_rate: number
  no_hit_rate: number
  avg_latency_ms: number
  period: string
}

interface NoHitQuery {
  query: string
  count: number
  last_seen: string
}

const PERIOD_OPTIONS = [
  { value: 'today', label: '今日' },
  { value: 'week', label: '本周' },
  { value: 'month', label: '近30天' },
]

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [period, setPeriod] = useState('month')
  const [loading, setLoading] = useState(false)
  const [noHitQueries, setNoHitQueries] = useState<NoHitQuery[]>([])

  const load = (p: string) => {
    setLoading(true)
    api
      .get(`/admin/stats?period=${p}`)
      .then((r) => setStats(r.data.data))
      .catch(() =>
        setStats({
          total_sessions: 0,
          resolved_rate: 0,
          no_hit_rate: 0,
          avg_latency_ms: 0,
          period: p,
        }),
      )
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load(period)
  }, [period])

  useEffect(() => {
    api
      .get('/admin/no-hit-queries')
      .then((r) => setNoHitQueries(r.data.data))
      .catch(() => setNoHitQueries([]))
  }, [])

  const cards = [
    {
      label: '累计会话数',
      value: stats?.total_sessions ?? '-',
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      dot: 'bg-blue-600',
    },
    {
      label: '已解决率',
      value: stats ? `${(stats.resolved_rate * 100).toFixed(1)}%` : '-',
      color: 'text-green-600',
      bg: 'bg-green-50',
      dot: 'bg-green-600',
    },
    {
      label: '无法回答率',
      value: stats ? `${(stats.no_hit_rate * 100).toFixed(1)}%` : '-',
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      dot: 'bg-amber-600',
    },
    {
      label: '平均响应时间',
      value: stats?.avg_latency_ms ? `${stats.avg_latency_ms}ms` : '-',
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      dot: 'bg-purple-600',
    },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">数据概览</h2>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
          {PERIOD_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setPeriod(o.value)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                period === o.value
                  ? 'bg-white text-gray-800 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div
        className={`grid grid-cols-2 gap-4 lg:grid-cols-4 mb-8 ${
          loading ? 'opacity-60' : ''
        }`}
      >
        {cards.map((c) => (
          <div
            key={c.label}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
          >
            <div
              className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center mb-3`}
            >
              <div className={`w-3 h-3 rounded-full ${c.dot}`} />
            </div>
            <p className={`text-2xl font-semibold ${c.color}`}>{c.value}</p>
            <p className="text-xs text-gray-400 mt-1">{c.label}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <p className="text-sm font-medium text-gray-700 mb-1">
          未解决问题（知识库优化入口）
        </p>
        <p className="text-xs text-gray-400">
          最近 30 天访客提问但 AI 判定无依据的高频问题；建议补充 FAQ 或上传相关文档
        </p>
        {noHitQueries.length > 0 ? (
          <div className="mt-4 space-y-1">
            {noHitQueries.slice(0, 10).map((q, i) => (
              <div
                key={i}
                className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0"
              >
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded flex-shrink-0">
                  {q.count}次
                </span>
                <span className="text-sm text-gray-700 flex-1 truncate">
                  {q.query}
                </span>
                <span className="text-xs text-gray-300 flex-shrink-0">
                  {new Date(q.last_seen).toLocaleDateString('zh')}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4 py-8 text-center text-gray-300 text-sm border-2 border-dashed border-gray-100 rounded-lg">
            暂无未解决问题
          </div>
        )}
      </div>
    </div>
  )
}
