<!--配置项删除确认弹窗-->
<template>
  <ElDialog
    :model-value="open"
    append-to-body
    align-center
    class="config-delete-dialog"
    modal-class="config-delete-overlay"
    width="420px"
    :show-close="false"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    @update:model-value="handleVisibilityChange"
  >
    <template #header="{ titleId, titleClass }">
      <div class="delete-dialog-heading">
        <span class="delete-warning-icon" aria-hidden="true">!</span>
        <span :id="titleId" :class="titleClass">{{ title }}</span>
      </div>
    </template>
    <p class="delete-dialog-description">{{ description }}</p>
    <template #footer>
      <button class="delete-dialog-cancel" type="button" :disabled="busy" @click="emit('close')">
        取消
      </button>
      <button class="delete-dialog-confirm" type="button" :disabled="busy" @click="emit('confirm')">
        {{ confirmText }}
      </button>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ElDialog } from 'element-plus'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    description: string
    confirmText?: string
    busy?: boolean
  }>(),
  { confirmText: '删除', busy: false },
)

const emit = defineEmits<{
  close: []
  confirm: []
}>()

function handleVisibilityChange(visible: boolean): void {
  if (!visible) emit('close')
}
</script>

<style scoped>
:global(.config-delete-overlay) {
  background: rgb(0 0 0 / 22%);
  backdrop-filter: blur(3px);
}
:global(.config-delete-dialog.el-dialog) {
  --el-dialog-padding-primary: 0px;
  width: min(420px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgb(0 0 0 / 16%);
}
.delete-dialog-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 24px 0;
  color: #202020;
  font-size: 15px;
  font-weight: 500;
  line-height: 20px;
}
.delete-warning-icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f99a00;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}
.delete-dialog-description {
  margin: 10px 0 0;
  padding: 0 24px 0 54px;
  color: #383838;
  font-size: 14px;
  line-height: 20px;
}
:global(.config-delete-dialog .el-dialog__footer) {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 24px 24px 22px;
}
.delete-dialog-cancel,
.delete-dialog-confirm {
  min-width: 80px;
  height: 38px;
  padding: 0 15px;
  border-radius: 9px;
  cursor: pointer;
  font: inherit;
  font-size: 14px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.delete-dialog-cancel {
  border: 1px solid #e2e2e2;
  background: #fff;
  color: #242424;
}
.delete-dialog-confirm {
  border: 1px solid #ff3b38;
  background: #ff3b38;
  color: #fff;
}
.delete-dialog-cancel:disabled,
.delete-dialog-confirm:disabled {
  cursor: wait;
  opacity: 0.6;
}
@media (hover: hover) {
  .delete-dialog-cancel:not(:disabled):hover {
    background: #f7f7f7;
  }
  .delete-dialog-confirm:not(:disabled):hover {
    border-color: #e83330;
    background: #e83330;
  }
}
.delete-dialog-cancel:focus-visible,
.delete-dialog-confirm:focus-visible {
  outline: 2px solid #303030;
  outline-offset: 2px;
}
@media (any-pointer: coarse) {
  .delete-dialog-cancel,
  .delete-dialog-confirm {
    min-height: 40px;
  }
}
</style>
