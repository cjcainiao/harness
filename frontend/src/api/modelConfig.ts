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

// 模型列表缓存
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
  const result = await requestUtil.post<ApiResult<ModelConfigItem>, ModelConfigInput>(
    '/api/config/models',
    input,
  )
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '添加模型失败')
  }
  const model = copy(result.data)
  previewModels.push(model)
  persistedModelNames.add(model.model_name)
  return copy(model)
}

/** 修改模型 */
export async function updateModelConfig(
  name: string,
  input: ModelConfigInput,
): Promise<ModelConfigItem> {
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  const changes: Partial<Omit<ModelConfigInput, 'model_name'>> = {
    display_name: input.display_name,
    description: input.description,
    provider: input.provider,
    use: input.use,
    timeout: input.timeout,
    max_retries: input.max_retries,
    max_tokens: input.max_tokens,
    supports_thinking: input.supports_thinking,
    reasoning_levels: input.reasoning_levels,
    when_thinking_enabled: input.when_thinking_enabled,
    when_thinking_disabled: input.when_thinking_disabled,
    supports_vision: input.supports_vision,
    context_window: input.context_window,
  }
  // 编辑时保留未填写的地址和密钥
  if (input.base_url) changes.base_url = input.base_url
  if (input.api_key) changes.api_key = input.api_key
  const result = await requestUtil.request<ApiResult<ModelConfigItem>, typeof changes>({
    method: 'PATCH',
    url: `/api/config/models/${encodeURIComponent(name)}`,
    data: changes,
  })
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '修改模型失败')
  }
  const model = copy(result.data)
  previewModels[index] = model
  persistedModelNames.add(model.model_name)
  return copy(model)
}

/** 设置默认模型并返回最新顺序 */
export async function setDefaultModel(name: string): Promise<ModelConfigItem[]> {
  if (!previewModels.some((model) => model.model_name === name)) {
    throw new Error(`模型不存在：${name}`)
  }
  const result = await requestUtil.request<ApiResult<ModelConfigItem[]>>({
    method: 'PATCH',
    url: `/api/config/models/${encodeURIComponent(name)}/default`,
  })
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '设置默认模型失败')
  }
  previewModels = result.data.map(copy)
  persistedModelNames = new Set(previewModels.map((model) => model.model_name))
  return previewModels.map(copy)
}

/** 删除模型，返回是否已从后端配置删除 */
export async function deleteModelConfig(name: string): Promise<boolean> {
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  const persisted = persistedModelNames.has(name)
  if (persisted) {
    const result = await requestUtil.delete<ApiResult<null>>(
      `/api/config/models/${encodeURIComponent(name)}`,
    )
    if (result.code !== 200) throw new Error(result.message || '删除模型失败')
    persistedModelNames.delete(name)
  }
  previewModels.splice(index, 1)
  return persisted
}
