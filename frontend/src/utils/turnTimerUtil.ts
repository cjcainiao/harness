import { onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

/** 走秒刷新间隔 */
const TIMER_TICK_MS = 200

/**
 * 执行中用本地时钟走秒，停下来就清掉定时器。
 * 用法：把"是否在跑"传进来，拿返回的 nowTick 参与耗时计算。
 */
export function useLiveTimer(isLive: () => boolean): Ref<number> {
  const nowTick = ref(Date.now())
  let timerId: number | null = null

  function stopTimer(): void {
    if (timerId === null) return
    window.clearInterval(timerId)
    timerId = null
  }

  watch(
    isLive,
    (active) => {
      stopTimer()
      if (!active) return
      nowTick.value = Date.now()
      timerId = window.setInterval(() => {
        nowTick.value = Date.now()
      }, TIMER_TICK_MS)
    },
    { immediate: true },
  )

  onUnmounted(stopTimer)

  return nowTick
}

/** 毫秒级显示，超过一秒换成秒 */
export function formatDuration(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)}s`
}
