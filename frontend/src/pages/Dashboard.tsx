import { useEffect, useState } from 'react'
import api from '../api/client'

interface Stats {
  total_sessions: number
  resolved_rate: number
  no_hit_rate: number
  avg_latency_ms: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    api
      .get('/admin/stats')
      .then((r) => setStats(r.data.data))
      .catch(() => {
        setStats({ total_sessions: 0, resolved_rate: 0, no_hit_rate: 0, avg_latency_ms: 0 })
      })
  }, [])

  const cards = [
    { label: '累计会话数', value: stats?.total_sessions ?? '-', color: 'text-blue-600' },
    {
      label: '解决率',
      value: stats ? `${(stats.resolved_rate * 100).toFixed(1)}%` : '-',
      color: 'text-green-600',
    },
    {
      label: '无法回答率',
      value: stats ? `${(stats.no_hit_rate * 100).toFixed(1)}%` : '-',
      color: 'text-amber-600',
    },
    {
      label: '平均响应时间',
      value: stats ? `${stats.avg_latency_ms}ms` : '-',
      color: 'text-purple-600',
    },
  ]

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">数据概览</h2>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
          >
            <p className="text-sm text-gray-500 mb-1">{c.label}</p>
            <p className={`text-2xl font-semibold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>
      <div className="mt-8 bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <p className="text-gray-400 text-sm text-center py-8">
          更多图表将在 Week 4 后续版本中添加
        </p>
      </div>
    </div>
  )
}
