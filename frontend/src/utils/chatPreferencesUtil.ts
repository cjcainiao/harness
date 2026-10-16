// 会话模型选择的本地存储

const STORAGE_PREFIX = 'chat:model-preference:v1:'

/** 单个会话的模型与推理档位 */
export interface ChatPreferences {
  modelName: string
  reasoningEffort: string
}

function storageKey(threadId: string): string {
  return `${STORAGE_PREFIX}${threadId}`
}

/** 读取会话的模型选择 */
export function readChatPreferences(threadId: string): ChatPreferences | null {
  if (!threadId) return null
  try {
    const raw = window.localStorage.getItem(storageKey(threadId))
    if (!raw) return null
    const value: unknown = JSON.parse(raw)
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return null
    const record = value as Record<string, unknown>
    if (
      typeof record.modelName !== 'string' ||
      !record.modelName.trim() ||
      typeof record.reasoningEffort !== 'string' ||
      !record.reasoningEffort.trim()
    )
      return null
    return { modelName: record.modelName, reasoningEffort: record.reasoningEffort }
  } catch {
    return null
  }
}

/** 保存会话的模型选择 */
export function writeChatPreferences(threadId: string, value: ChatPreferences): void {
  if (!threadId || !value.modelName) return
  try {
    window.localStorage.setItem(storageKey(threadId), JSON.stringify(value))
  } catch {
    // 存储不可用时仍允许当前页面继续对话
  }
}

/** 删除会话的模型选择 */
export function removeChatPreferences(threadId: string): void {
  if (!threadId) return
  try {
    window.localStorage.removeItem(storageKey(threadId))
  } catch {
    // 存储不可用时无需清理
  }
}
