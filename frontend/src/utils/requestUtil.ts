import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

/** 后端统一响应结构 */
export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T | null
}

// 提取接口返回的错误消息
function responseMessage(data: unknown): string | undefined {
  if (typeof data === 'string') {
    const message = data.trim()
    return message && !message.startsWith('<') ? message : undefined
  }
  if (!data || typeof data !== 'object') return undefined

  const payload = data as Record<string, unknown>
  for (const field of ['message', 'detail']) {
    const value = payload[field]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }

  if (Array.isArray(payload.detail)) {
    const messages = payload.detail
      .map((item: unknown) => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return ''
        const message = (item as Record<string, unknown>).msg
        return typeof message === 'string' ? message : ''
      })
      .filter(Boolean)
    if (messages.length) return messages.join('；')
  }
  return undefined
}

/** 统一的请求错误 */
export class RequestError extends Error {
  readonly status?: number
  readonly code?: number | string
  readonly data?: unknown
  readonly originalError: AxiosError

  constructor(
    message: string,
    originalError: AxiosError,
    options: {
      status?: number
      code?: number | string
      data?: unknown
    } = {},
  ) {
    super(message)
    this.name = 'RequestError'
    this.status = options.status
    this.code = options.code
    this.data = options.data
    this.originalError = originalError
  }
}

/** Axios 请求配置扩展，skipAuth 为后续接入登录态预留 */
export interface RequestConfig<D = unknown> extends AxiosRequestConfig<D> {
  skipAuth?: boolean
}

export class RequestUtil {
  private readonly client: AxiosInstance

  constructor() {
    this.client = axios.create({
      // 默认同源相对路径，跨源部署才配 VITE_API_BASE_URL
      baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
      timeout: 30_000,
      headers: {
        Accept: 'application/json',
      },
    })

    this.setupInterceptors()
  }

  /** 注册请求和响应拦截器 */
  private setupInterceptors(): void {
    this.client.interceptors.request.use(
      (config) => this.beforeRequest(config),
      (error: AxiosError) => Promise.reject(error),
    )

    this.client.interceptors.response.use(
      (response) => response.data,
      (error: unknown) => Promise.reject(this.normalizeError(error)),
    )
  }

  /** 请求前置处理 */
  private beforeRequest(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
    // 普通 JSON 请求默认声明响应格式；FormData 交给浏览器自动生成 Content-Type。
    if (!config.headers.has('Accept')) {
      config.headers.set('Accept', 'application/json')
    }

    const isFormData = typeof FormData !== 'undefined' && config.data instanceof FormData
    if (!isFormData && config.data !== undefined && !config.headers.has('Content-Type')) {
      config.headers.set('Content-Type', 'application/json')
    }

    // 当前后端尚未接入认证，这里保留扩展点，不主动读取或注入不存在的 token。
    return config
  }

  /** 将 Axios 错误转换成业务层可识别的错误 */
  private normalizeError(error: unknown): Error {
    if (!axios.isAxiosError(error)) {
      return error instanceof Error ? error : new Error(responseMessage(error) || '请求失败')
    }

    const responseData = error.response?.data
    const message =
      responseMessage(responseData) ||
      (error.code === 'ECONNABORTED' ? '请求超时' : undefined) ||
      (!error.response
        ? error.code === 'ERR_NETWORK'
          ? '网络连接失败'
          : error.message || '网络连接失败'
        : `请求失败（HTTP ${error.response.status}）`)

    const code =
      responseData && typeof responseData === 'object' && 'code' in responseData
        ? responseData.code
        : undefined
    const data =
      responseData && typeof responseData === 'object' && 'data' in responseData
        ? responseData.data
        : responseData

    return new RequestError(message, error, {
      status: error.response?.status,
      code: typeof code === 'number' || typeof code === 'string' ? code : error.code,
      data,
    })
  }

  /** 发起通用请求 */
  request<T = unknown, D = unknown>(config: RequestConfig<D>): Promise<T> {
    return this.unwrap<T>(this.client.request<T, T, D>(config))
  }

  get<T = unknown>(url: string, config?: RequestConfig): Promise<T> {
    return this.unwrap<T>(this.client.get<T, T>(url, config))
  }

  post<T = unknown, D = unknown>(url: string, data?: D, config?: RequestConfig<D>): Promise<T> {
    return this.unwrap<T>(this.client.post<T, T, D>(url, data, config))
  }

  put<T = unknown, D = unknown>(url: string, data?: D, config?: RequestConfig<D>): Promise<T> {
    return this.unwrap<T>(this.client.put<T, T, D>(url, data, config))
  }

  delete<T = unknown>(url: string, config?: RequestConfig): Promise<T> {
    return this.unwrap<T>(this.client.delete<T, T>(url, config))
  }

  /** 拦截器运行时已返回 response.data，这里统一收口类型断言 */
  private unwrap<T>(request: Promise<unknown>): Promise<T> {
    return request as Promise<T>
  }

  /** 暴露 Axios 实例，便于少数场景使用自定义能力 */
  getInstance(): AxiosInstance {
    return this.client
  }
}

export const requestUtil = new RequestUtil()

export default requestUtil
