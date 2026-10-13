// MCP 状态与配置接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

const MCP_API = '/api/config/mcp'

export type McpTransport = 'streamable_http' | 'stdio'
export type McpState = 'unchecked' | 'connected' | 'failed' | 'disabled'

/** 单台服务器的工具发现状态 */
export interface McpServerStatus {
  name: string
  enabled: boolean
  state: McpState
  tool_count: number
  tool_names: string[]
  error_type: 'config' | 'connection' | 'timeout' | null
  message: string | null
}

/** 最近一次工具发现结果 */
export interface McpStatusSnapshot {
  checked_at: string | null
  servers: McpServerStatus[]
}

/** 不含密钥的服务器配置 */
export interface McpServerConfig {
  name: string
  description: string | null
  enabled: boolean
  transport: McpTransport
  url: string | null
  has_hidden_url: boolean
  header_names: string[]
  command_configured: boolean
  args_count: number
  env_names: string[]
  cwd_configured: boolean
  connect_timeout_seconds: number
  call_timeout_seconds: number
}

/** 新增服务器参数 */
export interface McpServerCreate {
  name: string
  description?: string | null
  enabled: boolean
  transport: McpTransport
  url?: string | null
  headers?: Record<string, string>
  command?: string | null
  args?: string[]
  env?: Record<string, string>
  cwd?: string | null
  connect_timeout_seconds?: number
  call_timeout_seconds?: number
}

/** 修改服务器参数 */
export type McpServerPatch = Partial<Omit<McpServerCreate, 'name' | 'headers' | 'env'>> & {
  headers?: Record<string, string | null> | null
  env?: Record<string, string | null> | null
}

// 接口业务码校验
function unwrap<T>(result: ApiResult<T>, message: string): T {
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || message)
  }
  return result.data
}

/** 获取缓存中的服务器状态 */
export async function fetchMcpStatus(): Promise<McpStatusSnapshot> {
  const result = await requestUtil.get<ApiResult<McpStatusSnapshot>>(`${MCP_API}/status`)
  return unwrap(result, '获取 MCP 状态失败')
}

/** 重新发现全部 MCP 工具 */
export async function refreshMcpStatus(): Promise<McpStatusSnapshot> {
  const result = await requestUtil.post<ApiResult<McpStatusSnapshot>>(
    `${MCP_API}/refresh`,
    undefined,
    {
      timeout: 120_000,
    },
  )
  return unwrap(result, '刷新 MCP 服务失败')
}

/** 获取不含密钥的服务器配置 */
export async function fetchMcpConfigs(): Promise<McpServerConfig[]> {
  const result = await requestUtil.get<ApiResult<McpServerConfig[]>>(`${MCP_API}/servers`)
  return unwrap(result, '获取 MCP 配置失败')
}

/** 新增 MCP 服务器 */
export async function createMcpServer(input: McpServerCreate): Promise<McpServerConfig> {
  const result = await requestUtil.post<ApiResult<McpServerConfig>, McpServerCreate>(
    `${MCP_API}/servers`,
    input,
  )
  return unwrap(result, '新增 MCP 服务器失败')
}

/** 修改 MCP 服务器 */
export async function patchMcpServer(
  name: string,
  input: McpServerPatch,
): Promise<McpServerConfig> {
  const result = await requestUtil.request<ApiResult<McpServerConfig>, McpServerPatch>({
    method: 'PATCH',
    url: `${MCP_API}/servers/${encodeURIComponent(name)}`,
    data: input,
  })
  return unwrap(result, '修改 MCP 服务器失败')
}

/** 启用或停用 MCP 服务器 */
export async function setMcpServerEnabled(
  name: string,
  enabled: boolean,
): Promise<McpServerConfig> {
  const result = await requestUtil.request<ApiResult<McpServerConfig>, { enabled: boolean }>({
    method: 'PATCH',
    url: `${MCP_API}/servers/${encodeURIComponent(name)}/enabled`,
    data: { enabled },
  })
  return unwrap(result, '切换 MCP 服务器状态失败')
}

/** 删除 MCP 服务器 */
export async function deleteMcpServer(name: string): Promise<void> {
  const result = await requestUtil.delete<ApiResult<null>>(
    `${MCP_API}/servers/${encodeURIComponent(name)}`,
  )
  if (result.code !== 200) throw new Error(result.message || '删除 MCP 服务器失败')
}
