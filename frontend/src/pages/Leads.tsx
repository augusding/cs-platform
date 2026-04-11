import { useEffect, useState } from 'react'
import api from '../api/client'

interface Lead {
  id: string
  bot_id: string
  session_id: string
  lead_info: Record<string, string>
  status: string
  intent_score: number
  created_at: string
}

const STATUS_OPTIONS = ['new', 'contacted', 'qualified', 'closed']
const STATUS_LABEL: Record<string, string> = {
  new: '新线索',
  contacted: '已联系',
  qualified: '已确认',
  closed: '已关闭',
}
const STATUS_COLOR: Record<string, string> = {
  new: 'bg-blue-50 text-blue-600',
  contacted: 'bg-yellow-50 text-yellow-600',
  qualified: 'bg-green-50 text-green-600',
  closed: 'bg-gray-100 text-gray-500',
}

const FIELD_LABEL: Record<string, string> = {
  product_requirement: '产品需求',
  quantity: '采购数量',
  target_price: '目标价格',
  contact: '联系方式',
}

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)

  const load = (p: number, s: string) => {
    const q = s ? `&status=${s}` : ''
    api
      .get(`/leads?page=${p}&page_size=20${q}`)
      .then((r) => {
        setLeads(r.data.data)
        setTotal(r.data.meta?.total ?? 0)
      })
      .catch(() => setLeads([]))
  }

  useEffect(() => {
    load(page, filter)
  }, [page, filter])

  const updateStatus = async (id: string, status: string) => {
    await api.put(`/leads/${id}`, { status })
    load(page, filter)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-800">
          询盘线索{' '}
          <span className="text-base text-gray-400 font-normal">共 {total} 条</span>
        </h2>
        <select
          className="input w-36"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value)
            setPage(1)
          }}
        >
          <option value="">全部状态</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-3">
        {leads.map((lead) => (
          <div
            key={lead.id}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <span
                  className={`text-xs px-2 py-1 rounded-full font-medium ${STATUS_COLOR[lead.status]}`}
                >
                  {STATUS_LABEL[lead.status]}
                </span>
                <span className="text-sm text-gray-400">
                  意向分{' '}
                  <span className="font-medium text-gray-700">
                    {(lead.intent_score * 100).toFixed(0)}%
                  </span>
                </span>
                <span className="text-xs text-gray-300">
                  {new Date(lead.created_at).toLocaleString('zh')}
                </span>
              </div>
              <select
                className="text-xs border border-gray-200 rounded px-2 py-1 text-gray-600"
                value={lead.status}
                onChange={(e) => updateStatus(lead.id, e.target.value)}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABEL[s]}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm">
              {Object.entries(lead.lead_info)
                .filter(([k]) => !k.startsWith('_'))
                .map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-gray-400 w-20 flex-shrink-0">
                      {FIELD_LABEL[k] || k}
                    </span>
                    <span className="text-gray-700">{String(v)}</span>
                  </div>
                ))}
            </div>
          </div>
        ))}
        {leads.length === 0 && (
          <p className="text-gray-400 text-sm text-center py-8">暂无询盘线索</p>
        )}
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
