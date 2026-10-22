import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000
})

http.interceptors.response.use(
  (resp) => resp.data,
  (error) => {
    const detail = error.response?.data?.detail
    const timedOut = error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')
    let message
    if (detail) {
      message = detail
    } else if (!error.response) {
      message = timedOut ? '请求超时，请稍后重试' : '网络连接失败，请检查网络或确认后端服务已启动'
    } else {
      message = `请求失败（HTTP ${error.response.status}）`
    }
    return Promise.reject(new Error(message))
  }
)

export function predictImage(file) {
  const form = new FormData()
  form.append('file', file)
  return http.post('/predict', form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function getCrops() {
  return http.get('/crops')
}

export function getDiseases(params) {
  return http.get('/diseases', { params })
}

export function getDisease(className) {
  return http.get(`/diseases/${encodeURIComponent(className)}`)
}

export function getFaqs(category) {
  return http.get('/faqs', { params: category ? { category } : {} })
}

export function consult(question) {
  return http.post('/consult', { question })
}

export function createMessage(question, contact) {
  return http.post('/messages', { question, contact: contact || null })
}

export function getMessages(params) {
  return http.get('/messages', { params })
}

export function replyMessage(id, reply) {
  return http.post(`/messages/${id}/reply`, { reply })
}

export function getHealth() {
  return http.get('/health')
}
