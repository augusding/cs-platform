import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err.response?.status
    let message = '请求失败'
    if (err.response) {
      const data = err.response.data
      if (typeof data === 'string') message = data
      else if (data?.reason) message = data.reason
      else if (data?.error?.message) message = data.error.message
      else message = `HTTP ${status}`
    } else if (err.request) {
      message = '网络错误：服务器未响应，请确认后端是否启动'
    }
    err.userMessage = message

    if (status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    } else if (status === 402) {
      window.dispatchEvent(
        new CustomEvent('quota-exceeded', { detail: message }),
      )
    } else if (status === 429) {
      window.dispatchEvent(
        new CustomEvent('rate-limited', { detail: message }),
      )
    }
    return Promise.reject(err)
  },
)

export default api
