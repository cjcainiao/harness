import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

/**
 * 后端统一响应结构。
 * 流式接口不经过这个封装，仍然直接处理 SSE 事件。
 */
export interface ApiResult<T = unknown> {
  code: number
  message: string
  data: T | null
}

/**
 * 统一的请求错误，方便页面层按 status/code 做提示或跳转。
 */
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

/**
 * Axios 请求配置扩展。
 * skipAuth 为后续接入登录态预留，当前项目还没有认证接口。
 */
export interface RequestConfig<D = unknown> extends AxiosRequestConfig<D> {
  skipAuth?: boolean
}

export class RequestUtil {
  private readonly client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
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
      (error: AxiosError) => Promise.reject(this.normalizeError(error)),
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
  private normalizeError(error: AxiosError): RequestError {
    const responseData = error.response?.data as Partial<ApiResult> | undefined
    const message =
      (typeof responseData?.message === 'string' && responseData.message) ||
      (error.code === 'ECONNABORTED' ? '请求超时' : undefined) ||
      (!error.response ? '网络连接失败' : error.message) ||
      '请求失败'

    return new RequestError(message, error, {
      status: error.response?.status,
      code: responseData?.code ?? error.code,
      data: responseData?.data ?? error.response?.data,
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

  /**
   * Axios 类型定义保留原始响应类型，而响应拦截器运行时已返回 response.data。
   * 在这里统一收口，避免每个请求方法重复类型断言。
   */
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
