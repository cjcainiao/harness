<template>
  <div class="chat-index">
    <SessionHeader
      :title="sessionTitle"
      :sidebar-open="sidebarOpen"
      @toggle-sidebar="emit('toggle-sidebar')"
    />
    <!-- 消息显示区 -->
    <div class="chat-messages">
      <MessageEventHandler
        ref="messageHandler"
        :thread-id="threadId"
        @responding-change="isResponding = $event"
        @edit-message="handleEditMessage"
        @fork-created="handleForkCreated"
        @ask-follow-up="handleFollowUp"
      />
    </div>
    <!-- 底部固定区 -->
    <footer class="chat-bottom">
      <ChatInput
        ref="chatInput"
        :key="threadId"
        :is-responding="isResponding"
        @send="handleSend"
        @stop="handleStop"
      />
      <!-- 上下文占用暂用预览数据 -->
      <UsageBar
        :percentage="41"
        :system-prompt="3"
        :system-tools="7"
        :skills="0.5"
        :skill-count="11"
        :messages="30.5"
        :input-tokens="sessionUsage.inputTokens"
        :output-tokens="sessionUsage.outputTokens"
        :total-tokens="sessionUsage.totalTokens"
      />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatSessionsStore } from '@/stores/chatSessions'
import ChatInput from './components/input/ChatInput.vue'
import UsageBar from './components/input/UsageBar.vue'
import MessageEventHandler from './components/message/MessageEventHandler.vue'
import SessionHeader from './components/message/SessionHeader.vue'

withDefaults(defineProps<{ sidebarOpen?: boolean }>(), { sidebarOpen: false })
const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const route = useRoute()
const router = useRouter()
const chatSessions = useChatSessionsStore()
// 新对话没有路由 ID 时保留稳定的临时 ID
const newThreadId = crypto.randomUUID()
const threadId = computed(() => {
  const id = route.query.thread_id
  return typeof id === 'string' && id.trim() ? id : newThreadId
})
const messageHandler = ref<InstanceType<typeof MessageEventHandler> | null>(null)
const chatInput = ref<InstanceType<typeof ChatInput> | null>(null)
const isResponding = ref(false)
const sessionTitle = computed(
  () => chatSessions.sessions.find((session) => session.id === threadId.value)?.title ?? '新对话',
)
// 按当前 thread 汇总累计 Token 用量
const sessionUsage = computed(() => chatSessions.getUsage(threadId.value))

watch(
  () => route.query.thread_id,
  (id) => {
    if (typeof id === 'string' && id.trim()) chatSessions.ensureSession(id)
  },
  { immediate: true },
)

// 登记会话后创建本次提问的 turn
function handleSend(message: { content: string; files: File[] }) {
  chatSessions.ensureSession(threadId.value)
  chatSessions.titleFromMessage(
    threadId.value,
    message.content.trim() || message.files[0]?.name || '',
  )
  messageHandler.value?.startDemoTurn(message.content, { files: message.files })
}

function handleStop(): void {
  messageHandler.value?.stopDemoStreams()
}

// 将选中的用户消息带回输入框重新编辑
function handleEditMessage(content: string): void {
  chatInput.value?.setDraft(content)
}

function handleForkCreated(id: string): void {
  void router.push({ name: 'chat-index', query: { thread_id: id } })
}

function handleFollowUp(question: string): void {
  if (isResponding.value) return
  handleSend({ content: question, files: [] })
}
</script>

<style scoped>
.chat-index {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.chat-messages {
  flex: 1;
  min-height: 0;
}
.chat-bottom {
  flex-shrink: 0;
  padding-top: 12px;
}
</style>
