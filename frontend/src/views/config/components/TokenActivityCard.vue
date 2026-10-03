<!--Token 活动统计卡-->
<template>
  <section class="token-activity">
    <header class="activity-head">
      <h3 class="activity-title">Token 活动</h3>
      <div class="activity-modes" role="group" aria-label="统计粒度">
        <button
          v-for="option in modeOptions"
          :key="option.id"
          class="mode-option"
          :class="{ 'is-active': option.id === mode }"
          type="button"
          :aria-pressed="option.id === mode"
          @click="selectMode(option.id)"
        >
          {{ option.label }}
        </button>
      </div>
    </header>
    <div ref="bodyRef" class="activity-body" :class="{ 'is-loading': loading }">
      <!-- 格阵恒为 7 行 × 52 列，切换粒度只改数值口径与选中范围 -->
      <div
        :key="mode"
        class="activity-grid"
        aria-hidden="true"
        @mouseover="onHover"
        @mouseleave="clear"
      >
        <span
          v-for="cell in cells"
          :key="cell.index"
          :data-index="cell.index"
          :class="[
            'activity-cell',
            cell.pending ? 'is-pending' : `level-${cell.level}`,
            { 'is-range': cell.index >= range[0] && cell.index <= range[1] },
            { 'is-anchor': cell.index === hoverIndex },
          ]"
        />
      </div>
      <Transition name="tip">
        <div
          v-if="tip"
          class="activity-tip"
          :class="tip.align"
          :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
          aria-hidden="true"
        >
          {{ tip.text }}
        </div>
      </Transition>
      <!-- 月份刻度复用同一列宽，保证与格阵对齐 -->
      <div class="activity-months" aria-hidden="true">
        <span
          v-for="mark in monthMarks"
          :key="mark.col"
          class="month-label"
          :style="{ gridColumn: `${mark.col} / span ${mark.span}` }"
        >
          {{ mark.label }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

type ActivityMode = 'daily' | 'weekly' | 'total'

interface ModeOption {
  id: ActivityMode
  label: string
}

// 接口返回的单日用量，date 为 YYYY-MM-DD
interface ActivityDay {
  date: string
  tokens: number
}

interface Props {
  days?: ActivityDay[]
  loading?: boolean
}

// 用法：<TokenActivityCard :days="usageDays" :loading="pending" />，不传则显示空格阵
const props = withDefaults(defineProps<Props>(), { days: () => [], loading: false })

const modeOptions: ModeOption[] = [
  { id: 'daily', label: '每日' },
  { id: 'weekly', label: '每周' },
  { id: 'total', label: '累计' },
]

const weeks = 52
const daysPerWeek = 7
const total = weeks * daysPerWeek
const dayMs = 86400000

const today = new Date()
today.setHours(0, 0, 0, 0)
// 周日为一周起点，最后一列即本周
const gridStart = new Date(today.getTime() - (today.getDay() + (weeks - 1) * daysPerWeek) * dayMs)
const dateAt = (offset: number) => new Date(gridStart.getTime() + offset * dayMs)
const keyOf = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const dateLabel = (date: Date) =>
  `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
const valueLabel = (tokens: number) =>
  tokens
    ? `${tokens >= 10000 ? Math.round(tokens / 1000) / 10 + '万' : tokens.toLocaleString('zh-CN')} 个 Token`
    : '无活动'

const mode = ref<ActivityMode>('daily')

const daySeries = computed(() => {
  const tokensByDate = new Map(props.days.map((day) => [day.date, day.tokens]))
  return Array.from({ length: total }, (_, offset) => {
    const date = dateAt(offset)
    const pending = date > today
    return { date, pending, tokens: pending ? 0 : (tokensByDate.get(keyOf(date)) ?? 0) }
  })
})

// 逐日累加的滚动总量，供累计口径与提示语复用
const prefixSum = computed(() => {
  let running = 0
  return daySeries.value.map((day) => (running += day.tokens))
})

// 每日/每周按当天取色，累计按当天为止的滚动总量取色
const values = computed(() =>
  mode.value === 'total' ? prefixSum.value : daySeries.value.map((day) => day.tokens),
)

const cells = computed(() => {
  const list = values.value
  const max = list.reduce((peak, value) => Math.max(peak, value), 0)
  return list.map((tokens, index) => ({
    index,
    // 色阶按当前粒度的峰值分档
    level:
      !tokens || !max
        ? 0
        : tokens >= max * 0.75
          ? 4
          : tokens >= max * 0.5
            ? 3
            : tokens >= max * 0.25
              ? 2
              : 1,
    pending: daySeries.value[index]!.pending,
  }))
})

const hoverIndex = ref(-1)

// 选中范围：一天 → 一周 → 截至该天
const range = computed<[number, number]>(() => {
  const index = hoverIndex.value
  if (index < 0) return [1, 0]
  if (mode.value === 'daily') return [index, index]
  if (mode.value === 'weekly') {
    const start = Math.floor(index / daysPerWeek) * daysPerWeek
    return [start, start + daysPerWeek - 1]
  }
  return [0, index]
})

// 换月的那一列起一个刻度，间隔不足四列则省略
const monthMarks = computed(() => {
  const marks: { week: number; label: string }[] = []
  for (let week = 0; week < weeks; week++) {
    const month = dateAt(week * daysPerWeek).getMonth()
    const previous = marks[marks.length - 1]
    if (
      previous &&
      (month === dateAt((week - 1) * daysPerWeek).getMonth() || week - previous.week < 4)
    )
      continue
    marks.push({ week, label: `${month + 1}月` })
  }
  return marks.map((mark, index) => ({
    col: mark.week + 1,
    span: (marks[index + 1]?.week ?? weeks) - mark.week,
    label: mark.label,
  }))
})

const bodyRef = ref<HTMLElement | null>(null)
const tip = ref<{ x: number; y: number; text: string; align: string } | null>(null)

function selectMode(next: ActivityMode): void {
  mode.value = next
  clear()
}

function clear(): void {
  hoverIndex.value = -1
  tip.value = null
}

function tipText(index: number): string {
  const day = daySeries.value[index]!
  const date = dateLabel(day.date)
  if (mode.value === 'daily') return `${date} · ${valueLabel(day.tokens)}`
  // 周与累计都算到所在周末尾，与提示语一致
  const prefix = prefixSum.value
  const start = Math.floor(index / daysPerWeek) * daysPerWeek
  const end = Math.min(start + daysPerWeek - 1, total - 1)
  const weekTokens = prefix[end]! - (start ? prefix[start - 1]! : 0)
  if (mode.value === 'weekly') return `${date}当周：${valueLabel(weekTokens)}`
  return `截至 ${date} 当周累计 ${valueLabel(prefix[end]!)}`
}

// 提示框默认居中于格子上方，两端改为贴边展开以免被容器裁掉
function onHover(event: MouseEvent): void {
  const cellElement = event.target as HTMLElement
  const host = bodyRef.value
  const index = Number(cellElement.dataset.index)
  const cell = cells.value[index]
  // 未发生的未来日期没有数据，不弹提示
  if (
    props.loading ||
    !host ||
    !cell ||
    cell.pending ||
    !cellElement.classList.contains('activity-cell')
  ) {
    clear()
    return
  }
  hoverIndex.value = index
  const hostRect = host.getBoundingClientRect()
  const cellRect = cellElement.getBoundingClientRect()
  const col = Math.floor(index / daysPerWeek)
  const edge = 5
  tip.value = {
    x: cellRect.left - hostRect.left + cellRect.width / 2,
    y: cellRect.top - hostRect.top - 6,
    text: tipText(index),
    align: col < edge ? 'is-start' : col >= weeks - edge ? 'is-end' : '',
  }
}
</script>

<style scoped>
.token-activity {
  /* 列距跟随容器宽度，格子尺寸封顶；格宽与间隙按参考图 11:3 同比例缩放 */
  container-type: inline-size;
  --cols: 52;
  --rows: 7;
  --pitch-cap: 15px;
  --cell-pitch: min(calc(100cqi / var(--cols)), var(--pitch-cap));
  --cell-gap: calc(var(--cell-pitch) * 0.214);
  --cell-size: calc(var(--cell-pitch) - var(--cell-gap));
  --accent: 23 138 76;
}
.activity-head {
  /* 与格阵轨道同宽，屏幕再宽标题和页签也不会跑偏 */
  width: calc(var(--cell-pitch) * var(--cols) - var(--cell-gap));
  max-width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.activity-title {
  color: #1a1c1f;
  font-size: 14px;
  font-weight: 500;
}
.activity-modes {
  display: flex;
  align-items: center;
  gap: 14px;
}
.mode-option {
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #8e8f90;
  font-size: 13px;
  cursor: pointer;
}
.mode-option.is-active {
  color: #1a1c1f;
  font-weight: 500;
}
.mode-option:focus-visible {
  outline: 2px solid #a8b5c8;
  outline-offset: 2px;
}
.activity-body {
  position: relative;
  margin-top: calc(var(--cell-pitch) * 1.4);
}
.activity-grid {
  display: grid;
  grid-template-rows: repeat(var(--rows), var(--cell-size));
  grid-auto-flow: column;
  grid-auto-columns: var(--cell-size);
  gap: var(--cell-gap);
}
.activity-cell {
  position: relative;
  border-radius: calc(var(--cell-size) * 0.27);
}
/* 选中范围用一层同色薄纱叠在原色阶上，深色格也不会被抹平 */
.activity-cell::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: rgb(var(--accent));
  opacity: 0;
  pointer-events: none;
}
.activity-cell.is-range::after {
  opacity: 0.18;
}
.level-0 {
  background: #f4f4f4;
}
.level-1 {
  background: #d8ead9;
}
.level-2 {
  background: #a6d5ad;
}
.level-3 {
  background: #56b073;
}
.level-4 {
  background: #178a4c;
}
.is-pending {
  background: transparent;
}
/* 悬停的那一格单独加深，与参考图一致 */
.activity-cell.is-anchor {
  background: #0e6b3c;
}
.activity-cell.is-anchor::after {
  opacity: 0;
}
.activity-tip {
  position: absolute;
  z-index: 1;
  padding: 5px 8px;
  border-radius: 6px;
  background: #24292f;
  color: #fff;
  font-size: 12px;
  line-height: 1.4;
  white-space: nowrap;
  pointer-events: none;
  transform: translate(-50%, -100%);
}
.activity-tip.is-start {
  transform: translate(0, -100%);
}
.activity-tip.is-end {
  transform: translate(-100%, -100%);
}
.tip-enter-active,
.tip-leave-active {
  transition: opacity 0.12s ease;
}
.tip-enter-from,
.tip-leave-to {
  opacity: 0;
}
.activity-months {
  display: grid;
  grid-template-columns: repeat(var(--cols), var(--cell-size));
  column-gap: var(--cell-gap);
  margin-top: calc(var(--cell-pitch) * 0.72);
}
.month-label {
  overflow: hidden;
  color: #8e8f90;
  font-size: clamp(9px, calc(var(--cell-pitch) * 0.86), 12px);
  line-height: 1.4;
  white-space: nowrap;
  text-overflow: ellipsis;
}
@media (prefers-reduced-motion: no-preference) {
  .activity-cell::after,
  .mode-option {
    transition:
      opacity 0.12s ease,
      color 0.12s ease;
  }
  /* 切粒度时格阵重建，用一次淡入交代口径变化 */
  .activity-grid {
    animation: activity-in 0.18s ease;
  }
  .activity-body.is-loading .activity-grid {
    animation: activity-pulse 1.2s ease-in-out infinite;
  }
}
@media (prefers-reduced-motion: reduce) {
  .activity-body.is-loading .activity-grid {
    opacity: 0.4;
  }
}
@keyframes activity-in {
  from {
    opacity: 0.3;
  }
}
@keyframes activity-pulse {
  50% {
    opacity: 0.4;
  }
}
</style>
