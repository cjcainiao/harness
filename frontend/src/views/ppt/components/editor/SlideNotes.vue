<!--PPT 页面备注输入区-->
<template>
  <div class="slide-notes">
    <textarea
      :value="modelValue"
      rows="1"
      aria-label="当前幻灯片备注"
      placeholder="点击添加备注"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<style scoped>
.slide-notes {
  min-width: 0;
  border-top: 1px solid #d5d5d5;
  background: #f1f1f1;
}

.slide-notes textarea {
  display: block;
  width: 100%;
  height: 100%;
  resize: none;
  padding: 7px 10px;
  border: 0;
  outline: 0;
  background: transparent;
  color: #303030;
  font-size: 14px;
  line-height: 20px;
}

.slide-notes textarea::placeholder {
  color: #555;
}

@media (max-width: 700px) {
  .slide-notes textarea {
    padding: 13px 12px;
    font-size: 16px;
  }
}
</style>
