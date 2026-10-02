import { ref } from 'vue'

/**
 * 单排横向列表的拖动滚动：鼠标左键按住拖动，触屏保留原生滑动。
 * 用法：容器绑定 scrollRef 和 handlers，并用 isDragging 切换 grab/grabbing 光标。
 */
export function useDragScroll() {
  const scrollRef = ref<HTMLElement>()
  const isDragging = ref(false)
  let pointerId: number | null = null
  let startX = 0
  let startScrollLeft = 0
  let dragged = false
  let suppressClickUntil = 0

  function onPointerDown(event: PointerEvent): void {
    if (event.button !== 0 || event.pointerType !== 'mouse') return
    pointerId = event.pointerId
    startX = event.clientX
    startScrollLeft = scrollRef.value?.scrollLeft ?? 0
    dragged = false
  }

  function onPointerMove(event: PointerEvent): void {
    const el = scrollRef.value
    if (!el || pointerId !== event.pointerId) return

    const offset = event.clientX - startX
    if (!isDragging.value) {
      if (Math.abs(offset) < 4) return
      isDragging.value = true
      el.setPointerCapture(event.pointerId)
    }

    dragged = true
    el.scrollLeft = startScrollLeft - offset
  }

  function onPointerUp(event: PointerEvent): void {
    const el = scrollRef.value
    if (!el || pointerId !== event.pointerId) return
    if (el.hasPointerCapture(event.pointerId)) el.releasePointerCapture(event.pointerId)
    isDragging.value = false
    pointerId = null

    // 抬手后浏览器还会补一次点击，短时间内的一律当作拖动的尾巴
    if (dragged) {
      dragged = false
      suppressClickUntil = Date.now() + 250
    }
  }

  // 拖动收尾的那一次点击不再传给列表内的按钮
  function onClickCapture(event: MouseEvent): void {
    if (Date.now() >= suppressClickUntil) return
    suppressClickUntil = 0
    event.preventDefault()
    event.stopPropagation()
  }

  return { scrollRef, isDragging, onPointerDown, onPointerMove, onPointerUp, onClickCapture }
}
