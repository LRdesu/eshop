import axios from 'axios'
import router from '../router'

const http = axios.create({ baseURL: '/api/v1', timeout: 10000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

http.interceptors.response.use(
  (res) => {
    const d = res.data
    if (d && d.code !== undefined) {
      if (d.code === 0) return d.data
      if (d.code === 401) {
        localStorage.removeItem('token')
        router.replace('/login')
        return Promise.reject(new Error(d.msg || '未登录'))
      }
      return Promise.reject(new Error(d.msg || '请求失败'))
    }
    return d
  },
  (err) => Promise.reject(err)
)

export default http
