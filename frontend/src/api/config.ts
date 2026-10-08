// config 页面模块接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

/** 模型配置信息 */
export interface ModelInfo {
  // 实际模型名称
  model_name: string
  // 展示名称
  display_name: string
  // 模型说明
  description: string | null
  // 模型厂商
  provider: string
  // 模型实现类路径
  use: string
  // 是否支持推理
  supports_thinking: boolean
  // 可选推理强度
  reasoning_levels: string[]
  // 是否支持视觉
  supports_vision: boolean
  // 上下文长度
  context_window: number | null
}

/** 获取模型列表，第一项为默认模型 */
export async function fetchModels(): Promise<ModelInfo[]> {
  const result = await requestUtil.get<ApiResult<ModelInfo[]>>('/api/config/models')

  if (result.code !== 200) {
    throw new Error(result.message || '获取模型列表失败')
  }
  return result.data ?? []
}
