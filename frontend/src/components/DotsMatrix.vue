<!--点阵加载动画-->
<template>
  <span class="dots-matrix" aria-hidden="true">
    <i v-for="(shift, index) in cellPhases" :key="index" :style="{ '--cell': shift }" />
  </span>
</template>

<script setup lang="ts">
// 对角线点亮相位
const cellPhases = [0, 1, 2, 1, 2, 3, 2, 3, 4]
</script>

<style scoped>
.dots-matrix {
  display: grid;
  grid-template-columns: repeat(3, 3px);
  gap: 3px;
  flex: none;
}
.dots-matrix i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #5f6771;
  animation: cell-pulse 1.1s ease-in-out infinite;
  animation-delay: calc(var(--cell) * 0.13s);
}
@keyframes cell-pulse {
  0%,
  74%,
  100% {
    opacity: 0.15;
    transform: scale(0.7);
  }
  26% {
    opacity: 1;
    transform: scale(0.9);
  }
}
@media (prefers-reduced-motion: reduce) {
  .dots-matrix i {
    animation: none;
    opacity: 0.6;
  }
}
</style>
