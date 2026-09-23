<template>
  <div class="usage-bar">
    <span class="usage-item">Token 0 / 128K</span>
    <span class="usage-item">上下文 0%</span>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.usage-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  max-width: 760px;
  margin: 0 auto;
  padding: 6px 16px 14px;
  font-size: 12px;
  color: #9ca3af;
}
</style>
