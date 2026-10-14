<!--设置组件-->
<template>
  <Transition name="home-button">
    <RouterLink
      v-if="isOpen"
      class="home-button"
      :to="{ name: 'home-index' }"
      aria-label="回到主页"
      data-tooltip="回到主页"
      @pointerenter="scheduleAutoClose"
      @pointermove="scheduleAutoClose"
      @keydown="scheduleAutoClose"
      @focus="scheduleAutoClose"
    >
      <HouseIcon :size="21" :stroke-width="1.9" aria-hidden="true" />
    </RouterLink>
  </Transition>
  <button
    class="settings-toggle"
    :class="{ 'is-open': isOpen }"
    type="button"
    :aria-label="isOpen ? '收起快捷入口' : '展开快捷入口'"
    :aria-expanded="isOpen"
    :data-tooltip="isOpen ? '收起快捷入口' : '展开快捷入口'"
    @click="toggleSettings"
    @pointerenter="scheduleAutoClose"
    @pointermove="scheduleAutoClose"
    @keydown="scheduleAutoClose"
    @focus="scheduleAutoClose"
  >
    <span class="settings-surface">
      <ChevronLeftIcon class="edge-icon" :size="18" :stroke-width="2" aria-hidden="true" />
      <SettingsIcon class="settings-icon" :size="21" :stroke-width="1.9" aria-hidden="true" />
    </span>
  </button>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import {
  ChevronLeft as ChevronLeftIcon,
  House as HouseIcon,
  Settings as SettingsIcon,
} from 'lucide-vue-next'

const AUTO_CLOSE_DELAY = 5000
const isOpen = ref(false)
let closeTimer: ReturnType<typeof setTimeout> | undefined

function clearAutoClose() {
  if (closeTimer !== undefined) {
    clearTimeout(closeTimer)
    closeTimer = undefined
  }
}

function scheduleAutoClose() {
  if (!isOpen.value) return

  clearAutoClose()
  closeTimer = setTimeout(() => {
    isOpen.value = false
    closeTimer = undefined
  }, AUTO_CLOSE_DELAY)
}

function toggleSettings() {
  if (isOpen.value) {
    isOpen.value = false
    clearAutoClose()
    return
  }

  isOpen.value = true
  scheduleAutoClose()
}

onBeforeUnmount(clearAutoClose)
</script>

<style scoped>
.home-button {
  position: fixed;
  right: max(24px, calc(env(safe-area-inset-right) + 16px));
  bottom: calc(max(24px, calc(env(safe-area-inset-bottom) + 16px)) + 64px);
  z-index: 10;
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border: 1px solid #e2e2e2;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 6px 20px rgb(0 0 0 / 10%);
  color: #303133;
  text-decoration: none;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.home-button-enter-active,
.home-button-leave-active {
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}
.home-button-enter-active {
  transition-delay: 140ms;
}
.home-button-enter-from,
.home-button-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
.home-button-leave-active {
  pointer-events: none;
}
.home-button:focus-visible {
  outline: 3px solid #8ab4f8;
  outline-offset: 3px;
}
.home-button:active {
  background: #f0f0f0;
}
.home-button::after,
.settings-toggle::after {
  position: absolute;
  top: 50%;
  right: calc(100% + 12px);
  padding: 7px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 14px rgb(0 0 0 / 12%);
  color: #303133;
  content: attr(data-tooltip);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
  opacity: 0;
  pointer-events: none;
  transform: translate(6px, -50%);
  transition:
    opacity 160ms ease,
    transform 160ms ease;
  white-space: nowrap;
}
.settings-toggle {
  position: fixed;
  right: env(safe-area-inset-right, 0px);
  bottom: max(24px, calc(env(safe-area-inset-bottom) + 16px));
  z-index: 10;
  width: 40px;
  height: 52px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #303133;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    right 360ms cubic-bezier(0.32, 0, 0.18, 1),
    width 360ms cubic-bezier(0.32, 0, 0.18, 1);
}
.settings-surface {
  position: absolute;
  top: 0;
  right: -24px;
  width: 52px;
  height: 52px;
  border: 1px solid #e2e2e2;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 6px 20px rgb(0 0 0 / 10%);
  transition:
    right 360ms cubic-bezier(0.32, 0, 0.18, 1),
    background 180ms ease,
    box-shadow 180ms ease;
}
.edge-icon,
.settings-icon {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  transition: opacity 180ms ease;
}
.edge-icon {
  left: 13px;
  transition-delay: 120ms;
}
.settings-icon {
  left: 50%;
}
.settings-icon,
.is-open .edge-icon {
  opacity: 0;
}
.is-open .settings-icon {
  opacity: 1;
}
.settings-toggle.is-open {
  right: max(24px, calc(env(safe-area-inset-right) + 16px));
  width: 52px;
  transition-timing-function: cubic-bezier(0.22, 1.12, 0.36, 1);
}
.is-open .settings-surface {
  right: 0;
  transition-timing-function: cubic-bezier(0.22, 1.12, 0.36, 1);
}
.is-open .edge-icon {
  transition-delay: 0ms;
}
.is-open .settings-icon {
  transition-delay: 140ms;
}
.settings-toggle:focus-visible {
  outline: none;
}
.settings-toggle:focus-visible .settings-surface {
  outline: 3px solid #8ab4f8;
  outline-offset: 3px;
}
.settings-toggle:active .settings-surface {
  background: #f0f0f0;
}
@media (hover: hover) {
  .home-button:hover::after,
  .settings-toggle:hover::after {
    opacity: 1;
    transform: translate(0, -50%);
    transition-delay: 120ms;
  }
  .home-button:hover {
    background: #f8f8f8;
    box-shadow: 0 8px 24px rgb(0 0 0 / 14%);
  }
  .settings-toggle:hover .settings-surface {
    background: #f8f8f8;
    box-shadow: 0 8px 24px rgb(0 0 0 / 14%);
  }
}
.home-button:focus-visible::after,
.settings-toggle:focus-visible::after {
  opacity: 1;
  transform: translate(0, -50%);
}
.home-button:is(:hover, :focus-visible) ~ .settings-toggle::after {
  opacity: 0;
  transform: translate(6px, -50%);
  transition-delay: 0s;
}
@media (prefers-reduced-motion: reduce) {
  .home-button::after,
  .settings-toggle::after,
  .home-button-enter-active,
  .home-button-leave-active,
  .settings-toggle,
  .settings-surface,
  .edge-icon,
  .settings-icon {
    transition: none;
  }
}
@media (max-width: 720px) {
  .home-button {
    right: max(16px, calc(env(safe-area-inset-right) + 12px));
    bottom: calc(max(16px, calc(env(safe-area-inset-bottom) + 12px)) + 64px);
  }
  .settings-toggle {
    bottom: max(16px, calc(env(safe-area-inset-bottom) + 12px));
  }
  .settings-toggle.is-open {
    right: max(16px, calc(env(safe-area-inset-right) + 12px));
  }
}
</style>
