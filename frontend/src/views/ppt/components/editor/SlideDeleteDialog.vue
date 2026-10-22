<!--PPT 幻灯片删除确认弹窗-->
<template>
  <ElDialog
    :model-value="visible"
    append-to-body
    align-center
    class="slide-delete-dialog"
    modal-class="slide-delete-overlay"
    width="420px"
    :show-close="false"
    :close-on-click-modal="false"
    @close="emit('close')"
    @closed="emit('closed')"
  >
    <template #header="{ titleId, titleClass }">
      <div class="dialog-heading">
        <span class="warning-icon" aria-hidden="true">!</span>
        <span :id="titleId" :class="titleClass">确定删除第 {{ pageNumber }} 页？</span>
      </div>
    </template>
    <p class="dialog-description">删除后可使用工具栏的撤销恢复。</p>
    <template #footer>
      <button class="cancel-button" type="button" @click="emit('close')">取消</button>
      <button class="confirm-button" type="button" @click="emit('confirm')">删除</button>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ElDialog } from 'element-plus'

defineProps<{ visible: boolean; pageNumber: number }>()
const emit = defineEmits<{ close: []; confirm: []; closed: [] }>()
</script>

<style scoped>
:global(.slide-delete-overlay) {
  background: rgb(0 0 0 / 22%);
  backdrop-filter: blur(3px);
}

:global(.slide-delete-dialog.el-dialog) {
  --el-dialog-padding-primary: 0px;
  width: min(420px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgb(0 0 0 / 16%);
}

.dialog-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 24px 0;
  color: #202020;
  font-size: 15px;
  font-weight: 500;
  line-height: 20px;
}

.warning-icon {
  display: grid;
  width: 18px;
  height: 18px;
  place-items: center;
  flex: none;
  border-radius: 50%;
  background: #f99a00;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.dialog-description {
  margin: 10px 0 0;
  padding: 0 24px 0 54px;
  color: #383838;
  font-size: 14px;
  line-height: 20px;
}

:global(.slide-delete-dialog .el-dialog__footer) {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 24px 24px 22px;
}

.cancel-button,
.confirm-button {
  min-width: 80px;
  height: 38px;
  padding: 0 15px;
  border-radius: 9px;
  cursor: pointer;
  font-size: 14px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.cancel-button {
  border: 1px solid #e2e2e2;
  background: #fff;
  color: #242424;
}

.confirm-button {
  border: 1px solid #ff3b38;
  background: #ff3b38;
  color: #fff;
}

@media (hover: hover) {
  .cancel-button:hover {
    background: #f7f7f7;
  }

  .confirm-button:hover {
    border-color: #e83330;
    background: #e83330;
  }
}

@media (any-pointer: coarse) {
  .cancel-button,
  .confirm-button {
    min-height: 40px;
  }
}
</style>
