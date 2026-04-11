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
    const reason =
      err.response?.data?.reason ||
      err.response?.data?.error?.message ||
      '请求失败'

    if (status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    } else if (status === 402) {
      window.dispatchEvent(new CustomEvent('quota-exceeded', { detail: reason }))
    } else if (status === 429) {
      window.dispatchEvent(new CustomEvent('rate-limited', { detail: reason }))
    }
    return Promise.reject(err)
  },
)

export default api
