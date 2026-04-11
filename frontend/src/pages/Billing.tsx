import { useEffect, useState } from 'react'
import api from '../api/client'

interface Plan {
  id: string
  name: string
  price_yuan: number
  max_bots: number
  monthly_quota: number
}

interface Status {
  plan: string
  max_bots: number
  monthly_quota: number
  plan_expires_at?: string
}

export default function Billing() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [status, setStatus] = useState<Status | null>(null)
  const [loading, setLoading] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  const reload = () => api.get('/billing/status').then((r) => setStatus(r.data.data))

  useEffect(() => {
    api.get('/billing/plans').then((r) => setPlans(r.data.data))
    reload()
  }, [])

  const upgrade = async (planId: string) => {
    setLoading(planId)
    setMsg('')
    try {
      const { data } = await api.post('/billing/create-order', { plan: planId })
      const order = data.data
      await api.post('/billing/simulate-pay', { out_trade_no: order.out_trade_no })
      await reload()
      setMsg(`✓ 已升级到「${planId}」套餐`)
    } catch (e: any) {
      setMsg(e.response?.data?.reason || '操作失败')
    } finally {
      setLoading(null)
    }
  }

  const CURRENT = status?.plan || 'free'

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">套餐管理</h2>
      {status && (
        <p className="text-sm text-gray-500 mb-6">
          当前套餐：<span className="font-medium text-blue-600">{CURRENT}</span>
          {status.plan_expires_at &&
            ` · 到期 ${new Date(status.plan_expires_at).toLocaleDateString('zh')}`}
          {` · ${status.monthly_quota === -1 ? '无限' : status.monthly_quota} 条/月`}
        </p>
      )}
      {msg && (
        <div
          className={`text-sm p-3 rounded-lg mb-4 ${
            msg.startsWith('✓') ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'
          }`}
        >
          {msg}
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`bg-white rounded-xl p-5 shadow-sm border-2 ${
              plan.id === CURRENT ? 'border-blue-400' : 'border-gray-100'
            }`}
          >
            {plan.id === CURRENT && (
              <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full mb-2 inline-block">
                当前套餐
              </span>
            )}
            <p className="font-semibold text-gray-800 mt-1">{plan.name}</p>
            <p className="text-2xl font-bold text-blue-600 my-2">
              {plan.price_yuan === 0 ? '免费' : `¥${plan.price_yuan}`}
              {plan.price_yuan > 0 && (
                <span className="text-sm font-normal text-gray-400">/月</span>
              )}
            </p>
            <p className="text-sm text-gray-500">{plan.max_bots} 个 Bot</p>
            <p className="text-sm text-gray-500 mb-4">
              {plan.monthly_quota === -1
                ? '无限消息'
                : `${plan.monthly_quota.toLocaleString()} 条/月`}
            </p>
            {plan.id !== CURRENT && plan.price_yuan > 0 && (
              <button
                className="btn-primary w-full text-sm"
                onClick={() => upgrade(plan.id)}
                disabled={loading === plan.id}
              >
                {loading === plan.id ? '处理中...' : '升级'}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
