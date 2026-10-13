<!--三层卡片插画-->
<template>
  <div class="stack-illustration" :class="{ compact }" aria-hidden="true">
    <span class="sheet sheet-left" />
    <span class="sheet sheet-right" />
    <span class="sheet sheet-front">
      <component :is="icon" :size="compact ? 16 : 23" :stroke-width="1.8" />
    </span>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{ icon: Component; compact?: boolean }>()
</script>

<style scoped>
.stack-illustration {
  position: relative;
  width: 68px;
  height: 62px;
  flex: 0 0 auto;
}
.sheet {
  position: absolute;
  top: 7px;
  left: 10px;
  display: grid;
  width: 48px;
  height: 49px;
  place-items: center;
  border: 1px solid #e2e2e2;
  border-radius: 7px;
  background: #fff;
}
.sheet-left,
.sheet-right {
  transform-origin: center bottom;
  transition: transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.sheet-left {
  transform: rotate(-12deg) translateX(-6px);
}
.sheet-right {
  transform: rotate(12deg) translateX(6px);
}
.sheet-front {
  top: 3px;
  color: #666;
}
.compact {
  width: 42px;
  height: 42px;
}
.compact .sheet {
  top: 6px;
  left: 7px;
  width: 29px;
  height: 30px;
  border-radius: 5px;
}
.compact .sheet-front {
  top: 3px;
}
@media (hover: hover) {
  .stack-illustration:hover .sheet-left {
    transform: rotate(-18deg) translateX(-11px);
  }
  .stack-illustration:hover .sheet-right {
    transform: rotate(18deg) translateX(11px);
  }
  .compact:hover .sheet-left {
    transform: rotate(-18deg) translateX(-8px);
  }
  .compact:hover .sheet-right {
    transform: rotate(18deg) translateX(8px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .sheet-left,
  .sheet-right {
    transition: none;
  }
}
</style>
