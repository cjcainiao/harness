import {
  EventStreamContentType,
  fetchEventSource,
  type EventSourceMessage,
} from '@microsoft/fetch-event-source'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

/** 解析后的 SSE 消息 */
export interface SseMessage<T = unknown> {
  id: string
  event: string
  retry?: number
  data: T
  rawData: string
}

/** SSE 请求错误 */
export class SseError extends Error {
  readonly status?: number
  readonly response?: Response
  readonly cause?: unknown

  constructor(
    message: string,
    options: {
      status?: number
      response?: Response
      cause?: unknown
    } = {},
  ) {
    super(message)
    this.name = 'SseError'
    this.status = options.status
    this.response = options.response
    this.cause = options.cause
  }
}

export interface SseRequestOptions<TBody = unknown, TData = unknown> {
  /** 可以传相对路径，也可以传完整 URL */
  url: string
  method?: RequestInit['method']
  data?: TBody
  headers?: Record<string, string>
  signal?: AbortSignal
  credentials?: RequestCredentials
  openWhenHidden?: boolean

  /** false 表示失败后直接抛错；true 使用库默认间隔重试；数字表示重试间隔毫秒 */
  retry?: boolean | number

  /** 收到每条 SSE 消息时触发 */
  onMessage?: (message: SseMessage<TData>) => void
  /** 收到 type=done 事件时触发 */
  onDone?: (message: SseMessage<TData>) => void
  /** 服务端正常关闭连接时触发，completed 表示是否收到 done 事件 */
  onClose?: (completed: boolean) => void
  /** 连接、解析或服务端错误时触发 */
  onError?: (error: SseError) => void
}

function resolveUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) {
    return url
  }

  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL
  return `${baseUrl.replace(/\/+$/, '')}/${url.replace(/^\/+/, '')}`
}

function serializeBody(data: unknown): BodyInit | undefined {
  if (data === undefined || data === null) {
    return undefined
  }

  if (
    typeof data === 'string' ||
    data instanceof Blob ||
    data instanceof FormData ||
    data instanceof URLSearchParams ||
    data instanceof ArrayBuffer
  ) {
    return data
  }

  return JSON.stringify(data)
}

function parseEventData<T>(message: EventSourceMessage): SseMessage<T> {
  let data: T

  try {
    data = JSON.parse(message.data) as T
  } catch {
    data = message.data as T
  }

  return {
    id: message.id,
    event: message.event,
    retry: message.retry,
    data,
    rawData: message.data,
  }
}

function isDoneMessage(message: SseMessage): boolean {
  return (
    typeof message.data === 'object' &&
    message.data !== null &&
    'type' in message.data &&
    (message.data as { type?: unknown }).type === 'done'
  )
}

export class SseUtil {
  /** 发起一次 SSE 请求 */
  async request<TBody = unknown, TData = unknown>(
    options: SseRequestOptions<TBody, TData>,
  ): Promise<void> {
    const {
      url,
      method = 'POST',
      data,
      headers = {},
      signal,
      credentials,
      openWhenHidden = false,
      retry = false,
      onMessage,
      onDone,
      onClose,
      onError,
    } = options

    let completed = false
    const requestHeaders = Object.entries({
      accept: EventStreamContentType,
      ...headers,
    }).reduce<Record<string, string>>((normalizedHeaders, [name, value]) => {
      normalizedHeaders[name.toLowerCase()] = value
      return normalizedHeaders
    }, {})
    const body = serializeBody(data)

    if (body !== undefined && typeof body === 'string' && !requestHeaders['content-type']) {
      requestHeaders['content-type'] = 'application/json'
    }

    await fetchEventSource(resolveUrl(url), {
      method,
      headers: requestHeaders,
      body,
      signal,
      credentials,
      openWhenHidden,

      async onopen(response) {
        const contentType = response.headers.get('content-type') ?? ''
        if (!response.ok) {
          throw new SseError(`SSE 请求失败：HTTP ${response.status}`, {
            status: response.status,
            response,
          })
        }

        if (!contentType.startsWith(EventStreamContentType)) {
          throw new SseError('响应不是有效的 SSE 流', {
            status: response.status,
            response,
          })
        }
      },

      onmessage(event) {
        const message = parseEventData<TData>(event)
        onMessage?.(message)

        if (isDoneMessage(message)) {
          completed = true
          onDone?.(message)
        }
      },

      onclose() {
        onClose?.(completed)
      },

      onerror(error) {
        const normalizedError =
          error instanceof SseError
            ? error
            : new SseError(error instanceof Error ? error.message : 'SSE 请求失败', {
                cause: error,
              })

        onError?.(normalizedError)

        if (retry === false) {
          throw normalizedError
        }

        return typeof retry === 'number' ? retry : undefined
      },
    })
  }
}

export const sseUtil = new SseUtil()

export default sseUtil
