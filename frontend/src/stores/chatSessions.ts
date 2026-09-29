import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatTurn, TurnUsage } from '@/views/chat/components/message/messageTurn'

export interface ChatSession {
  id: string
  title: string
  createdAt: number
}

export const useChatSessionsStore = defineStore('chatSessions', () => {
  const sessions = ref<ChatSession[]>([])
  const turnsByThread = ref<Record<string, ChatTurn[]>>({})
  // 正在回复的会话，侧边栏动画用
  const respondingThreadId = ref<string | null>(null)

  function setResponding(id: string, active: boolean): void {
    if (active) respondingThreadId.value = id
    else if (respondingThreadId.value === id) respondingThreadId.value = null
  }

  function ensureSession(id: string): ChatSession {
    const existing = sessions.value.find((session) => session.id === id)
    if (existing) return existing
    const session = { id, title: '新对话', createdAt: Date.now() }
    sessions.value.unshift(session)
    return session
  }

  function createSession(): string {
    const id = crypto.randomUUID()
    ensureSession(id)
    return id
  }

  // 用首条消息生成会话标题
  function titleFromMessage(id: string, message: string): void {
    const session = ensureSession(id)
    if (session.title !== '新对话') return
    const title = message.replace(/\s+/g, ' ').trim()
    if (title) session.title = title.slice(0, 40)
  }

  // 保存 turn 快照，切换窗口后仍能读取用量
  function saveTurns(id: string, turns: ChatTurn[]): void {
    turnsByThread.value[id] = turns.map((turn) => ({
      ...turn,
      attachments: turn.attachments?.map((attachment) => ({ ...attachment })),
      items: turn.items.map((item) => ({ ...item })),
      usage: turn.usage && { ...turn.usage },
      followUpQuestions: turn.followUpQuestions?.slice(),
    }))
  }

  function getTurns(id: string): ChatTurn[] {
    return turnsByThread.value[id] ?? []
  }

  // 汇总同一聊天窗口内所有 turn 的 Token 用量
  function getUsage(id: string): TurnUsage {
    return getTurns(id).reduce<TurnUsage>(
      (total, turn) => {
        total.inputTokens += turn.usage?.inputTokens ?? 0
        total.outputTokens += turn.usage?.outputTokens ?? 0
        total.totalTokens += turn.usage?.totalTokens ?? 0
        return total
      },
      { inputTokens: 0, outputTokens: 0, totalTokens: 0 },
    )
  }

  return {
    sessions,
    respondingThreadId,
    createSession,
    ensureSession,
    setResponding,
    titleFromMessage,
    saveTurns,
    getTurns,
    getUsage,
  }
})
