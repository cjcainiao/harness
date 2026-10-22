<!--PPT 主题输入区-->
<template>
  <section class="source-entry" aria-label="PPT 创作输入">
    <div class="composer">
      <div class="prompt-row">
        <textarea
          v-model="model"
          rows="2"
          aria-label="PPT 主题"
          placeholder="输入你想创作的 PPT 主题"
        />
      </div>
      <div class="composer-actions">
        <div class="action-left">
          <button class="add-button" type="button" disabled aria-label="添加资料">
            <Plus :size="20" :stroke-width="1.7" />
            <span class="notice-dot" />
          </button>
          <span class="ppt-tag"><Presentation :size="14" :stroke-width="1.8" /> PPT</span>
        </div>
        <div class="action-right">
          <span class="mode-label">标准模式</span>
          <button class="send-button" type="button" disabled aria-label="开始生成 PPT">
            <ArrowUp :size="20" :stroke-width="1.8" />
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ArrowUp, Plus, Presentation } from 'lucide-vue-next'

const model = defineModel<string>({ default: '' })
</script>

<style scoped>
.source-entry {
  min-width: 0;
}
.composer {
  position: relative;
  min-height: 113px;
  padding: 12px 16px 10px;
  border: 1px solid #e8e8e8;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 9px 22px rgb(28 31 36 / 9%);
}
.prompt-row {
  min-width: 0;
}
.prompt-row textarea {
  width: 100%;
  min-width: 0;
  min-height: 56px;
  padding: 3px 0;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  color: #262626;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.6;
}
.prompt-row textarea::placeholder {
  color: #9d9d9d;
}
.composer-actions,
.action-left,
.action-right {
  display: flex;
  align-items: center;
}
.composer-actions {
  justify-content: space-between;
  gap: 16px;
  margin-top: 1px;
}
.action-left,
.action-right {
  gap: 13px;
}
.add-button {
  position: relative;
  display: grid;
  width: 28px;
  height: 30px;
  place-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  color: #343434;
  cursor: not-allowed;
}
.notice-dot {
  position: absolute;
  top: 3px;
  right: 1px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #438af1;
}
.ppt-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #f18409;
  font-size: 12px;
  font-weight: 650;
}
.mode-label {
  color: #777;
  font-size: 12px;
  white-space: nowrap;
}
.send-button {
  display: grid;
  width: 37px;
  height: 37px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: #d9d9d9;
  color: #fff;
  cursor: not-allowed;
}
@media (max-width: 600px) {
  .composer {
    padding: 12px 13px 10px;
    border-radius: 15px;
  }
  .prompt-row textarea {
    font-size: 16px;
  }
}
@media (any-pointer: coarse) {
  .add-button,
  .send-button {
    min-width: 40px;
    min-height: 40px;
  }
}
</style>
