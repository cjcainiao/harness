// 模型配置预览接口

/** 模型配置页面使用的不含密钥数据 */
export interface ModelConfigItem {
  model_name: string
  display_name: string
  description: string | null
  provider: string
  use: string
  base_url: string | null
  api_key_configured: boolean
  timeout: number
  max_retries: number
  max_tokens: number | null
  supports_thinking: boolean
  reasoning_levels: string[]
  when_thinking_enabled: Record<string, unknown> | null
  when_thinking_disabled: Record<string, unknown> | null
  supports_vision: boolean
  context_window: number | null
}

/** 新增或修改模型时提交的数据 */
export type ModelConfigInput = Omit<ModelConfigItem, 'api_key_configured'> & {
  api_key?: string
}

const thinkingOn = { extra_body: { thinking: { type: 'enabled' } } }
const thinkingOff = { extra_body: { thinking: { type: 'disabled' } } }

// 示例模型数据
const previewModels: ModelConfigItem[] = [
  {
    model_name: 'deepseek-flash',
    display_name: 'DeepSeek-V4.1-Flash',
    description: 'DeepSeek 快速模型，支持推理与视觉',
    provider: 'deepseek',
    use: 'harness.models.deepseek_provider:DeepSeekChatModel',
    base_url: 'https://api.deepseek.com',
    api_key_configured: true,
    timeout: 60,
    max_retries: 2,
    max_tokens: 393216,
    supports_thinking: true,
    reasoning_levels: ['low', 'high', 'max'],
    when_thinking_enabled: thinkingOn,
    when_thinking_disabled: thinkingOff,
    supports_vision: true,
    context_window: 1048576,
  },
  {
    model_name: 'deepseek-v4-pro',
    display_name: 'DeepSeek-V4-Pro',
    description: 'DeepSeek 强推理模型，支持推理，不支持视觉',
    provider: 'deepseek',
    use: 'harness.models.deepseek_provider:DeepSeekChatModel',
    base_url: 'https://api.deepseek.com',
    api_key_configured: true,
    timeout: 60,
    max_retries: 2,
    max_tokens: 393216,
    supports_thinking: true,
    reasoning_levels: ['low', 'high', 'max'],
    when_thinking_enabled: thinkingOn,
    when_thinking_disabled: thinkingOff,
    supports_vision: false,
    context_window: 1048576,
  },
  {
    model_name: 'qwen3.8-max',
    display_name: 'Qwen3.8-Max',
    description: '千问旗舰模型，支持推理与视觉',
    provider: 'alibaba',
    use: 'harness.models.qwen_provider:QwenChatModel',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    api_key_configured: true,
    timeout: 60,
    max_retries: 2,
    max_tokens: 131072,
    supports_thinking: true,
    reasoning_levels: ['low', 'high', 'max'],
    when_thinking_enabled: { enable_thinking: true },
    when_thinking_disabled: { enable_thinking: false },
    supports_vision: true,
    context_window: 1048576,
  },
  {
    model_name: 'qwen3.8-flash',
    display_name: 'Qwen3.8-Flash',
    description: '千问轻量模型，支持推理与视觉',
    provider: 'alibaba',
    use: 'harness.models.qwen_provider:QwenChatModel',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    api_key_configured: true,
    timeout: 60,
    max_retries: 2,
    max_tokens: 131072,
    supports_thinking: true,
    reasoning_levels: ['low', 'high', 'max'],
    when_thinking_enabled: { enable_thinking: true },
    when_thinking_disabled: { enable_thinking: false },
    supports_vision: true,
    context_window: 1048576,
  },
]

function copy(model: ModelConfigItem): ModelConfigItem {
  return structuredClone(model)
}

/** 获取模型列表，第一项为默认模型 */
export async function listModelConfigs(): Promise<ModelConfigItem[]> {
  return previewModels.map(copy)
}

/** 新增模型 */
export async function createModelConfig(input: ModelConfigInput): Promise<ModelConfigItem> {
  if (previewModels.some((model) => model.model_name === input.model_name)) {
    throw new Error(`模型已存在：${input.model_name}`)
  }
  const { api_key, ...fields } = input
  const model = copy({ ...fields, api_key_configured: Boolean(api_key) })
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
  const { api_key, ...fields } = input
  const model = copy({
    ...fields,
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

/** 删除模型 */
export async function deleteModelConfig(name: string): Promise<void> {
  if (previewModels.length === 1) throw new Error('至少保留一个模型')
  const index = previewModels.findIndex((model) => model.model_name === name)
  if (index < 0) throw new Error(`模型不存在：${name}`)
  previewModels.splice(index, 1)
}
