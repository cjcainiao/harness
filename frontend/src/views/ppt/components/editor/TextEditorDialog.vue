<!--PPT 文字内容编辑弹窗-->
<template>
  <Teleport to="body">
    <div class="dialog-backdrop" @click.self="emit('cancel')">
      <section
        class="text-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="text-dialog-title"
        @keydown.esc.stop="emit('cancel')"
      >
        <header>
          <h2 id="text-dialog-title">{{ mode === 'create' ? '添加文字' : '编辑文字' }}</h2>
          <button type="button" aria-label="关闭" @click="emit('cancel')"><X :size="18" /></button>
        </header>
        <form @submit.prevent="save">
          <label for="ppt-text-content">文字内容</label>
          <textarea
            id="ppt-text-content"
            ref="textInput"
            v-model="text"
            rows="5"
            maxlength="2000"
          />
          <label for="ppt-font-size">字号</label>
          <input id="ppt-font-size" v-model.number="fontSize" type="number" min="12" max="96" />
          <footer>
            <button class="cancel-button" type="button" @click="emit('cancel')">取消</button>
            <button class="save-button" type="submit" :disabled="!text.trim()">确定</button>
          </footer>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  mode: 'create' | 'edit'
  initialText: string
  initialFontSize: number
}>()
const emit = defineEmits<{ save: [text: string, fontSize: number]; cancel: [] }>()
const text = ref(props.initialText)
const fontSize = ref(props.initialFontSize)
const textInput = ref<HTMLTextAreaElement | null>(null)

onMounted(() => nextTick(() => textInput.value?.focus()))

function save() {
  const content = text.value.trim()
  if (!content) return
  const size = Number.isFinite(fontSize.value) ? Math.max(12, Math.min(96, fontSize.value)) : 32
  emit('save', content, size)
}
</script>

<style scoped>
.dialog-backdrop {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: grid;
  place-items: center;
  overflow-y: auto;
  padding: 16px;
  background: rgb(0 0 0 / 28%);
}

.text-dialog {
  width: min(100%, 480px);
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  border: 1px solid #e3e3e3;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 16px 50px rgb(0 0 0 / 18%);
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}

h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
}

header button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: #666;
  cursor: pointer;
}

form {
  display: flex;
  flex-direction: column;
  padding: 18px 20px 20px;
}

label {
  margin-bottom: 7px;
  color: #4a4a4a;
  font-size: 13px;
}

textarea,
input {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid #d7d7d7;
  border-radius: 6px;
  outline-color: #b74426;
  background: #fff;
  color: #222;
  font-family: inherit;
  font-size: 16px;
}

textarea {
  min-height: 130px;
  resize: vertical;
  margin-bottom: 18px;
}

input {
  width: 92px;
  min-height: 40px;
}

footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 22px;
}

footer button {
  min-width: 72px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid #dadada;
  border-radius: 6px;
  background: #fff;
  color: #444;
  cursor: pointer;
}

footer .save-button {
  border-color: #b74426;
  background: #b74426;
  color: #fff;
}

footer .save-button:disabled {
  opacity: 0.5;
  cursor: default;
}

@media (hover: hover) {
  header button:hover,
  .cancel-button:hover {
    background: #f2f2f2;
  }
}

@media (any-pointer: coarse) {
  header button,
  footer button {
    min-width: 40px;
    min-height: 40px;
  }
}
</style>
