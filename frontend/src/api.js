import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 0 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('rdms_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (status === 401) {
      localStorage.removeItem('rdms_token')
      localStorage.removeItem('rdms_user')
      if (!location.pathname.startsWith('/login')) location.href = '/login'
    }
    const message = typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join('；')
      : error.message
    return Promise.reject(new Error(message || '请求失败'))
  },
)

/** 提取错误文案 */
export function errMsg(e) {
  return e?.message || String(e)
}

export default api
