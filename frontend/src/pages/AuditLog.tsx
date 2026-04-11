import { useEffect, useState } from 'react'
import api from '../api/client'

interface AuditEntry {
  id: string
  user_id: string | null
  action: string
  resource: string
  resource_id: string | null
  ip: string | null
  created_at: string
}

const ACTION_COLOR: Record<string, string> = {
  'bot.create': 'bg-green-50 text-green-600',
  'bot.delete': 'bg-red-50 text-red-500',
  'member.role_change': 'bg-blue-50 text-blue-600',
  'member.status_change': 'bg-amber-50 text-amber-600',
  'plan.upgrade': 'bg-purple-50 text-purple-600',
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [resource, setResource] = useState('')

  const load = (r: string) => {
    const q = r ? `?resource=${r}` : ''
    api
      .get(`/admin/audit${q}`)
      .then((d) => setEntries(d.data.data))
      .catch(() => setEntries([]))
  }

  useEffect(() => {
    load(resource)
  }, [resource])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">操作审计</h2>
        <select
          className="input w-40"
          value={resource}
          onChange={(e) => setResource(e.target.value)}
        >
          <option value="">全部操作</option>
          <option value="bot">Bot 操作</option>
          <option value="user">成员操作</option>
          <option value="tenant">套餐操作</option>
        </select>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              {['操作', '资源ID', 'IP', '时间'].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-xs">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr
                key={e.id}
                className="border-t border-gray-50 hover:bg-gray-50/50"
              >
                <td className="px-4 py-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      ACTION_COLOR[e.action] || 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {e.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                  {e.resource_id ? e.resource_id.slice(0, 8) + '...' : '—'}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {e.ip || '—'}
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {new Date(e.created_at).toLocaleString('zh')}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-8 text-center text-gray-400 text-sm"
                >
                  暂无审计记录
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
