import axios from 'axios'
import router from '../router'

/**
 * 商家后台专用实例：与买家端 token 隔离（localStorage: admin_token），
 * 便于同一浏览器同时保持买家与商家登录态。
 */
const http = axios.create({ baseURL: '/api/v1', timeout: 10000 })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

function toLogin() {
  localStorage.removeItem('admin_token')
  if (router.currentRoute.value.path !== '/admin/login') {
    router.replace('/admin/login')
  }
}

http.interceptors.response.use(
  (res) => {
    const d = res.data
    if (d && d.code !== undefined) {
      if (d.code === 0) return d.data
      if (d.code === 401 || d.code === 403) {
        toLogin()
        return Promise.reject(new Error(d.msg || '登录已失效'))
      }
      return Promise.reject(new Error(d.msg || '请求失败'))
    }
    return d
  },
  (err) => {
    const st = err.response && err.response.status
    if (st === 401 || st === 403) {
      toLogin()
      return Promise.reject(new Error('登录已失效或无权限'))
    }
    return Promise.reject(err)
  }
)

export default http
