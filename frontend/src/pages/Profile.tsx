import { useEffect, useState } from 'react'
import api from '../api/client'

interface Me {
  id: string
  email: string
  name: string
  role: string
  created_at: string
}

const ROLE_LABEL: Record<string, string> = {
  super_admin: '所有者',
  admin: '管理员',
  operator: '客服',
  viewer: '观察者',
}

export default function Profile() {
  const [me, setMe] = useState<Me | null>(null)
  const [name, setName] = useState('')
  const [oldPwd, setOldPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [saving, setSaving] = useState(false)
  const [changing, setChanging] = useState(false)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  useEffect(() => {
    api.get('/auth/me').then((r) => {
      setMe(r.data.data)
      setName(r.data.data.name)
    })
  }, [])

  const saveName = async () => {
    setSaving(true)
    setMsg(null)
    try {
      await api.put('/auth/me', { name })
      setMsg({ text: '姓名已保存', ok: true })
    } catch (e: any) {
      setMsg({ text: e.response?.data?.reason || '保存失败', ok: false })
    } finally {
      setSaving(false)
    }
  }

  const changePwd = async () => {
    if (!oldPwd || !newPwd) return
    setChanging(true)
    setMsg(null)
    try {
      await api.put('/auth/change-password', {
        old_password: oldPwd,
        new_password: newPwd,
      })
      setMsg({ text: '密码已更新，请重新登录', ok: true })
      setTimeout(() => {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }, 1500)
    } catch (e: any) {
      setMsg({ text: e.response?.data?.reason || '修改失败', ok: false })
    } finally {
      setChanging(false)
      setOldPwd('')
      setNewPwd('')
    }
  }

  if (!me) return <div className="text-gray-400 text-sm p-8">加载中...</div>

  return (
    <div className="max-w-lg">
      <h2 className="text-xl font-semibold text-gray-800 mb-6">个人设置</h2>

      {msg && (
        <div
          className={`text-sm p-3 rounded-lg mb-4 ${
            msg.ok ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'
          }`}
        >
          {msg.text}
        </div>
      )}

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-4">
        <h3 className="font-medium text-gray-800 mb-4">基本信息</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">邮箱</label>
            <input
              className="input bg-gray-50 cursor-not-allowed"
              value={me.email}
              disabled
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">姓名</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">角色</label>
            <input
              className="input bg-gray-50 cursor-not-allowed"
              value={ROLE_LABEL[me.role] || me.role}
              disabled
            />
          </div>
        </div>
        <button
          className="btn-primary mt-4 w-full"
          onClick={saveName}
          disabled={saving}
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-medium text-gray-800 mb-4">修改密码</h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">当前密码</label>
            <input
              className="input"
              type="password"
              value={oldPwd}
              onChange={(e) => setOldPwd(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              新密码（至少8位）
            </label>
            <input
              className="input"
              type="password"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
            />
          </div>
        </div>
        <button
          className="btn-primary mt-4 w-full"
          onClick={changePwd}
          disabled={changing || !oldPwd || !newPwd}
        >
          {changing ? '修改中...' : '修改密码'}
        </button>
      </div>
    </div>
  )
}
