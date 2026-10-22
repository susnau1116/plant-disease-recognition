// 后端地址配置：
// - 浏览器 H5 调试：127.0.0.1 即可
// - 真机 / 模拟器调试：改为电脑的局域网 IP，如 http://192.168.1.100:8000/api
// - 打包发布：改为服务器地址
export const BASE_URL = 'http://192.168.1.125:8000/api'

function networkErrorMessage(err) {
  const raw = (err && err.errMsg) || ''
  if (raw.toLowerCase().includes('timeout')) return '请求超时，请稍后重试'
  return '网络连接失败，请检查网络或确认后端服务已启动'
}

function request(options) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: { 'Content-Type': 'application/json' },
      timeout: 30000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const detail = res.data && res.data.detail
          reject(new Error(detail || '请求失败（HTTP ' + res.statusCode + '）'))
        }
      },
      fail: (err) => reject(new Error(networkErrorMessage(err)))
    })
  })
}

export function uploadImage(filePath) {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + '/predict',
      filePath,
      name: 'file',
      timeout: 60000,
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            resolve(JSON.parse(res.data))
          } catch (e) {
            reject(new Error('识别结果解析失败'))
          }
        } else {
          let msg = '识别失败（HTTP ' + res.statusCode + '）'
          try {
            msg = JSON.parse(res.data).detail || msg
          } catch (e) {
            /* 保留默认错误信息 */
          }
          reject(new Error(msg))
        }
      },
      fail: (err) => reject(new Error(networkErrorMessage(err)))
    })
  })
}

export const getHealth = () => request({ url: '/health' })
export const getCrops = () => request({ url: '/crops' })
export const getDiseases = (params) => request({ url: '/diseases', data: params })
export const getDisease = (className) =>
  request({ url: '/diseases/' + encodeURIComponent(className) })
export const getFaqs = (category) =>
  request({ url: '/faqs', data: category ? { category } : {} })
export const consult = (question) =>
  request({ url: '/consult', method: 'POST', data: { question } })
export const createMessage = (question, contact) =>
  request({ url: '/messages', method: 'POST', data: { question, contact: contact || null } })
export const getMessages = (params) => request({ url: '/messages', data: params })
