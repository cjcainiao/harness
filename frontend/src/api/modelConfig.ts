// 模型配置接口

import requestUtil, { type ApiResult } from '@/utils/requestUtil'

/** 模型配置页面使用的不含密钥数据 */
export interface ModelConfigItem {
  model_name: string
  display_name: string
  description: string | null
  provider: string
  use: string
  base_url_configured: boolean
  api_key_configured: boolean
  timeout: number | null
  max_retries: number | null
  max_tokens: number | null
  supports_thinking: boolean
  reasoning_levels: string[]
  when_thinking_enabled: Record<string, unknown> | null
  when_thinking_disabled: Record<string, unknown> | null
  supports_vision: boolean
  context_window: number | null
}

/** 新增或修改模型时提交的数据 */
export type ModelConfigInput = Omit<
  ModelConfigItem,
  'base_url_configured' | 'api_key_configured' | 'timeout' | 'max_retries'
> & {
  base_url: string | null
  api_key?: string
  timeout: number
  max_retries: number
}

// 未接入新增、修改和默认模型接口时的页面预览数据
let previewModels: ModelConfigItem[] = []
let persistedModelNames = new Set<string>()

function copy(model: ModelConfigItem): ModelConfigItem {
  return structuredClone(model)
}

/** 获取模型列表，第一项为默认模型 */
export async function listModelConfigs(): Promise<ModelConfigItem[]> {
  const result = await requestUtil.get<ApiResult<ModelConfigItem[]>>('/api/config/models')
  if (result.code !== 200) throw new Error(result.message || '获取模型配置失败')
  previewModels = (result.data ?? []).map(copy)
  persistedModelNames = new Set(previewModels.map((model) => model.model_name))
  return previewModels.map(copy)
}

/** 判断模型是否已保存到后端 */
export function isPersistedModelConfig(name: string): boolean {
  return persistedModelNames.has(name)
}

/** 新增模型 */
export async function createModelConfig(input: ModelConfigInput): Promise<ModelConfigItem> {
  if (previewModels.some((model) => model.model_name === input.model_name)) {
    throw new Error(`模型已存在：${input.model_name}`)
  }
  const { api_key, base_url, ...fields } = input
  const model = copy({
    ...fields,
    base_url_configured: Boolean(base_url),
    api_key_configured: Boolean(api_key),
  })
  previewModels.push(model)
  return copy(model)
}

/** 修改模型 */
export async function updateModelConfig(
  name: string,
  input: ModelConfigInput,
): Promise<ModelConfigItem> {
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  const { api_key, base_url, ...fields } = input
  const model = copy({
    ...fields,
    base_url_configured: Boolean(base_url) || previewModels[index]!.base_url_configured,
    api_key_configured: Boolean(api_key) || previewModels[index]!.api_key_configured,
  })
  previewModels[index] = model
  return copy(model)
}

/** 将模型移到首位 */
export async function setDefaultModel(name: string): Promise<ModelConfigItem[]> {
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  previewModels.unshift(previewModels.splice(index, 1)[0]!)
  return previewModels.map(copy)
}

/** 删除模型，返回是否已从后端配置删除 */
export async function deleteModelConfig(name: string): Promise<boolean> {
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  const persisted = persistedModelNames.has(name)
  if (persisted) {
    const result = await requestUtil.delete<ApiResult<null>>('/api/config/models', {
      params: { model_name: name },
    })
    if (result.code !== 200) throw new Error(result.message || '删除模型失败')
    persistedModelNames.delete(name)
  }
  previewModels.splice(index, 1)
  return persisted
}
