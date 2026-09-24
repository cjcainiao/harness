<template>
  <ElCollapseTransition>
    <div v-if="request" class="approval-shell">
      <section
        class="approval-card"
        role="region"
        :aria-label="`审批 ${request.tool} 操作`"
        :aria-busy="processing !== null"
      >
        <div class="approval-header">
          <ShieldAlert :size="17" :stroke-width="1.8" aria-hidden="true" />
          <strong>需要批准</strong>
          <span class="approval-tool">{{ request.tool }}</span>
        </div>
        <div class="approval-content">
          <p class="approval-summary">{{ request.summary }}</p>
          <pre v-if="request.details" class="approval-details">{{ request.details }}</pre>
        </div>
        <div class="approval-actions">
          <ElButton
            :disabled="processing !== null"
            :loading="processing === 'reject'"
            @click="decide('reject')"
          >
            拒绝
          </ElButton>
          <ElButton
            color="#1f2328"
            :disabled="processing !== null"
            :loading="processing === 'approve'"
            @click="decide('approve')"
          >
            允许一次
          </ElButton>
        </div>
      </section>
    </div>
  </ElCollapseTransition>
</template>

<script setup lang="ts">
import { ShieldAlert } from 'lucide-vue-next'
import { ElButton, ElCollapseTransition } from 'element-plus'
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/collapse-transition/style/css'

interface ApprovalRequest {
  id: string
  tool: string
  summary: string
  details?: string
}

type ApprovalDecision = 'approve' | 'reject'

const props = withDefaults(
  defineProps<{ request: ApprovalRequest | null; processing?: ApprovalDecision | null }>(),
  { processing: null },
)
const emit = defineEmits<{
  decide: [payload: { id: string; decision: ApprovalDecision }]
}>()

function decide(decision: ApprovalDecision) {
  if (!props.request || props.processing !== null) return
  emit('decide', { id: props.request.id, decision })
}
</script>

<style scoped>
.approval-shell {
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  padding: 0 16px 8px;
}
.approval-card {
  display: flex;
  flex-direction: column;
  max-height: min(42vh, 360px);
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
}
.approval-header {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 9px;
  color: #30343a;
  font-size: 13px;
}
.approval-header svg {
  flex-shrink: 0;
  color: #dd6b3b;
}
.approval-tool {
  min-width: 0;
  overflow: hidden;
  margin-left: auto;
  color: #858a91;
  font-size: 12px;
  font-weight: 400;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.approval-content {
  min-height: 0;
  overflow-y: auto;
  padding: 0 14px 12px;
}
.approval-summary {
  color: #30343a;
  font-size: 13px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
.approval-details {
  margin-top: 9px;
  padding: 9px 11px;
  border: 1px solid #ebedf0;
  border-radius: 8px;
  background: #f7f8fa;
  color: #565d66;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.approval-actions {
  display: flex;
  flex-shrink: 0;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid #f0f1f3;
}
.approval-actions :deep(.el-button) {
  min-height: 34px;
  margin-left: 0;
  border-radius: 8px;
}
@media (any-pointer: coarse) {
  .approval-actions :deep(.el-button) {
    min-height: 40px;
  }
}
</style>
