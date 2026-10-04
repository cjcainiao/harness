<!--进行中文案扫光-->
<template>
  <span class="shimmer-text" :class="{ 'is-plain': !active }"><slot /></span>
</template>

<script setup lang="ts">
// 进行中文案的扫光，非进行中不着色不动
withDefaults(defineProps<{ active?: boolean }>(), { active: true })
</script>

<style scoped>
/* 两端铺底色，扫过的只有中间亮带 */
.shimmer-text {
  background-image: linear-gradient(
    110deg,
    var(--shimmer-base, #6d757e) 0 42%,
    var(--shimmer-highlight, #b6bec7) 50%,
    var(--shimmer-base, #6d757e) 58% 100%
  );
  background-size: 250% 100%;
  background-repeat: no-repeat;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: text-shimmer 4s linear infinite;
}

/* 结束后回到普通文字 */
.shimmer-text.is-plain {
  background: none;
  color: inherit;
  animation: none;
}

@keyframes text-shimmer {
  0% {
    background-position: 0% 0;
  }
  100% {
    background-position: 100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .shimmer-text {
    background: none;
    color: inherit;
    animation: none;
  }
}
</style>
