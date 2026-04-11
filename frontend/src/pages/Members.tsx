import { useEffect, useState } from 'react'
import api from '../api/client'

interface Member {
  id: string
  email: string
  name: string
  role: string
  status: string
  last_login_at?: string
  created_at: string
}

interface Invitation {
  id: string
  email: string
  role: string
  status: string
  expires_at: string
}

const ROLE_LABEL: Record<string, string> = {
  super_admin: '所有者',
  admin: '管理员',
  operator: '客服',
  viewer: '观察者',
}
const ROLE_COLOR: Record<string, string> = {
  super_admin: 'bg-purple-50 text-purple-600',
  admin: 'bg-blue-50 text-blue-600',
  operator: 'bg-green-50 text-green-600',
  viewer: 'bg-gray-100 text-gray-500',
}

export default function Members() {
  const [members, setMembers] = useState<Member[]>([])
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [invEmail, setInvEmail] = useState('')
  const [invRole, setInvRole] = useState('operator')
  const [inviting, setInviting] = useState(false)
  const [inviteResult, setInviteResult] = useState<
    { token: string; email: string } | null
  >(null)
  const [error, setError] = useState('')
  const myRole = localStorage.getItem('role') || ''

  const load = async () => {
    try {
      const [m, i] = await Promise.all([
        api.get('/members').then((r) => r.data.data),
        api.get('/members/invitations').then((r) => r.data.data).catch(() => []),
      ])
      setMembers(m)
      setInvitations(i)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    load()
  }, [])

  const invite = async () => {
    if (!invEmail.trim()) {
      setError('请输入邮箱')
      return
    }
    setInviting(true)
    setError('')
    try {
      const { data } = await api.post('/auth/invite', {
        email: invEmail.trim(),
        role: invRole,
      })
      setInviteResult({ token: data.data.token, email: invEmail.trim() })
      setInvEmail('')
      await load()
    } catch (e: any) {
      setError(e.response?.data?.reason || '邀请失败')
    } finally {
      setInviting(false)
    }
  }

  const changeRole = async (userId: string, role: string) => {
    try {
      await api.put(`/members/${userId}/role`, { role })
      await load()
    } catch (e: any) {
      alert(e.response?.data?.reason || '修改失败')
    }
  }

  const toggleStatus = async (member: Member) => {
    const newStatus = member.status === 'active' ? 'suspended' : 'active'
    if (
      !confirm(
        `确认${newStatus === 'suspended' ? '停用' : '启用'}「${
          member.name || member.email
        }」？`,
      )
    )
      return
    try {
      await api.put(`/members/${member.id}/status`, { status: newStatus })
      await load()
    } catch (e: any) {
      alert(e.response?.data?.reason || '操作失败')
    }
  }

  const isAdmin = myRole === 'super_admin' || myRole === 'admin'

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">成员管理</h2>

      {isAdmin && (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 mb-6">
          <p className="text-sm font-medium text-gray-700 mb-3">邀请新成员</p>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-gray-500 mb-1 block">邮箱</label>
              <input
                className="input"
                type="email"
                placeholder="colleague@company.com"
                value={invEmail}
                onChange={(e) => {
                  setInvEmail(e.target.value)
                  setError('')
                }}
              />
            </div>
            <div className="w-32">
              <label className="text-xs text-gray-500 mb-1 block">角色</label>
              <select
                className="input"
                value={invRole}
                onChange={(e) => setInvRole(e.target.value)}
              >
                <option value="admin">管理员</option>
                <option value="operator">客服</option>
                <option value="viewer">观察者</option>
              </select>
            </div>
            <button className="btn-primary h-9" onClick={invite} disabled={inviting}>
              {inviting ? '发送中...' : '发送邀请'}
            </button>
          </div>
          {error && <p className="text-red-500 text-xs mt-2">{error}</p>}

          {inviteResult && (
            <div className="mt-3 p-3 bg-green-50 rounded-lg">
              <p className="text-xs text-green-700 font-medium mb-1">
                邀请链接已生成，请发送给 {inviteResult.email}：
              </p>
              <div className="flex gap-2">
                <code className="text-xs bg-white px-2 py-1 rounded border border-green-200 flex-1 truncate">
                  {window.location.origin}/accept-invite?token=
                  {inviteResult.token}
                </code>
                <button
                  className="text-xs text-green-600 hover:underline flex-shrink-0"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `${window.location.origin}/accept-invite?token=${inviteResult.token}`,
                    )
                    alert('已复制')
                  }}
                >
                  复制
                </button>
              </div>
              <button
                className="text-xs text-gray-400 mt-1 hover:underline"
                onClick={() => setInviteResult(null)}
              >
                关闭
              </button>
            </div>
          )}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mb-4">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              {['姓名', '邮箱', '角色', '状态', '最后登录', '操作'].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-xs">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr
                key={m.id}
                className="border-t border-gray-50 hover:bg-gray-50/50"
              >
                <td className="px-4 py-3 font-medium text-gray-800">
                  {m.name || '—'}
                </td>
                <td className="px-4 py-3 text-gray-500">{m.email}</td>
                <td className="px-4 py-3">
                  {isAdmin && m.role !== 'super_admin' ? (
                    <select
                      className="text-xs border border-gray-200 rounded px-1.5 py-0.5"
                      value={m.role}
                      onChange={(e) => changeRole(m.id, e.target.value)}
                    >
                      <option value="admin">管理员</option>
                      <option value="operator">客服</option>
                      <option value="viewer">观察者</option>
                    </select>
                  ) : (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        ROLE_COLOR[m.role] || ''
                      }`}
                    >
                      {ROLE_LABEL[m.role] || m.role}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      m.status === 'active'
                        ? 'bg-green-50 text-green-600'
                        : m.status === 'invited'
                        ? 'bg-amber-50 text-amber-600'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {m.status === 'active'
                      ? '正常'
                      : m.status === 'invited'
                      ? '待激活'
                      : '已停用'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">
                  {m.last_login_at
                    ? new Date(m.last_login_at).toLocaleDateString('zh')
                    : '从未'}
                </td>
                <td className="px-4 py-3">
                  {isAdmin && m.role !== 'super_admin' && m.status !== 'invited' && (
                    <button
                      className={`text-xs hover:underline ${
                        m.status === 'active' ? 'text-red-400' : 'text-green-500'
                      }`}
                      onClick={() => toggleStatus(m)}
                    >
                      {m.status === 'active' ? '停用' : '启用'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {invitations.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-600 mb-2">
            待接受邀请 ({invitations.length})
          </p>
          <div className="space-y-2">
            {invitations.map((inv) => (
              <div
                key={inv.id}
                className="bg-white rounded-lg px-4 py-3 border border-gray-100 flex items-center gap-4 text-sm"
              >
                <span className="flex-1 text-gray-700">{inv.email}</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    ROLE_COLOR[inv.role] || ''
                  }`}
                >
                  {ROLE_LABEL[inv.role] || inv.role}
                </span>
                <span className="text-xs text-gray-400">
                  过期：{new Date(inv.expires_at).toLocaleDateString('zh')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
