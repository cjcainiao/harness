<!--技能包添加表单-->
<template>
  <div v-if="open" class="dialog-backdrop" @click.self="close">
    <section
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="skill-form-title"
      @keydown.esc="close"
    >
      <header class="dialog-header">
        <div>
          <h2 id="skill-form-title">添加技能包</h2>
          <p>选择本地技能压缩包。</p>
        </div>
        <button
          type="button"
          class="close-button"
          :disabled="saving"
          aria-label="关闭"
          @click="close"
        >
          <X :size="18" />
        </button>
      </header>

      <form @submit.prevent="submit">
        <div class="dialog-body">
          <span class="field-label">技能压缩包</span>
          <label class="file-field" :class="{ 'has-file': selectedFile }">
            <input
              ref="fileInput"
              type="file"
              accept=".skill,.zip,.7z,.tar,.tar.gz,.tar.bz2,.tar.xz,.tgz,.tbz2,.txz"
              :disabled="saving"
              aria-label="选择技能压缩包"
              @change="selectFile"
            />
            <FileArchive v-if="selectedFile" :size="24" :stroke-width="1.6" />
            <Upload v-else :size="24" :stroke-width="1.6" />
            <strong>{{ selectedFile?.name ?? '点击选择文件' }}</strong>
            <span>{{
              selectedFile ? formatSize(selectedFile.size) : '支持 .skill、.zip、.7z、tar 压缩包'
            }}</span>
          </label>
          <p class="form-note">目前只预览页面交互，选择的文件不会上传，也不会安装到后端。</p>
        </div>
        <footer class="dialog-footer">
          <button type="button" class="cancel-button" :disabled="saving" @click="close">
            取消
          </button>
          <button type="submit" class="submit-button" :disabled="saving || !selectedFile">
            {{ saving ? '处理中…' : '添加到预览列表' }}
          </button>
        </footer>
      </form>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { FileArchive, Upload, X } from 'lucide-vue-next'

const props = defineProps<{ open: boolean; saving: boolean }>()
const emit = defineEmits<{ close: []; submit: [file: File] }>()

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    selectedFile.value = null
    await nextTick()
    fileInput.value?.focus()
  },
)

function selectFile(event: Event): void {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] ?? null
}

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function close(): void {
  if (!props.saving) emit('close')
}

function submit(): void {
  if (selectedFile.value && !props.saving) emit('submit', selectedFile.value)
}
</script>

<style scoped>
.dialog-backdrop {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.38);
}
.dialog {
  width: min(100%, 560px);
  max-height: calc(100dvh - 40px);
  overflow-y: auto;
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.14);
  color: #171717;
}
.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  border-bottom: 1px solid #ececec;
  padding: 24px 28px;
}
.dialog-header h2 {
  font-size: 19px;
  font-weight: 680;
}
.dialog-header p {
  margin-top: 6px;
  color: #777;
  font-size: 12px;
}
.close-button {
  display: grid;
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  place-items: center;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #777;
  cursor: pointer;
}
.dialog-body {
  padding: 27px 28px 30px;
}
.field-label {
  display: block;
  margin-bottom: 11px;
  color: #333;
  font-size: 12px;
  font-weight: 650;
}
.file-field {
  position: relative;
  display: flex;
  min-height: 160px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px dashed #cfcfcf;
  border-radius: 8px;
  background: #fafafa;
  color: #666;
  text-align: center;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.file-field.has-file {
  border-style: solid;
  background: #fff;
}
.file-field input {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
.file-field strong {
  max-width: calc(100% - 32px);
  overflow: hidden;
  color: #222;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-field span {
  color: #888;
  font-size: 12px;
}
.form-note {
  margin-top: 15px;
  color: #888;
  font-size: 12px;
  line-height: 1.6;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  border-top: 1px solid #ececec;
  padding: 16px 28px;
}
.dialog-footer button {
  min-width: 82px;
  min-height: 36px;
  border: 1px solid #d8d8d8;
  border-radius: 6px;
  padding: 0 12px;
  background: #fff;
  color: #333;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
}
.dialog-footer .submit-button {
  border-color: #171717;
  background: #171717;
  color: #fff;
}
.dialog-footer button:disabled {
  cursor: default;
  opacity: 0.5;
}
@media (hover: hover) {
  .close-button:hover,
  .dialog-footer .cancel-button:hover {
    background: #f2f2f2;
  }
  .file-field:hover {
    border-color: #999;
  }
  .dialog-footer .submit-button:not(:disabled):hover {
    background: #333;
  }
}
.close-button:focus-visible,
.file-field:focus-within,
.dialog-footer button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .dialog-backdrop {
    align-items: end;
    padding: 0;
  }
  .dialog {
    width: 100%;
    max-height: calc(100dvh - 16px);
    border-radius: 12px 12px 0 0;
  }
  .dialog-header,
  .dialog-body {
    padding-right: 20px;
    padding-left: 20px;
  }
  .dialog-footer {
    padding-right: 20px;
    padding-bottom: max(16px, env(safe-area-inset-bottom));
    padding-left: 20px;
  }
}
@media (any-pointer: coarse) {
  .close-button,
  .dialog-footer button {
    min-width: 44px;
    min-height: 44px;
  }
}
</style>
