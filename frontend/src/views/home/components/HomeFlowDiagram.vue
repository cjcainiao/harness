<!--项目执行流程图-->
<template>
  <div class="flow-diagram">
    <VueFlow
      class="flow-canvas"
      :class="{ 'is-touch': isTouch }"
      :nodes="nodes"
      :edges="edges"
      :fit-view-on-init="true"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :elements-selectable="false"
      :zoom-on-scroll="false"
      :pan-on-drag="isTouch"
      :min-zoom="0.25"
    >
      <Background :gap="14" :size="1.2" pattern-color="#dcdfe6" />
      <template #node-lane="{ data }">
        <p class="lane-label" :class="{ 'is-right': data.side === 'right' }">{{ data.title }}</p>
      </template>
      <template #node-stage="{ data }">
        <div class="flow-node">
          <Handle id="t-top" type="target" :position="Position.Top" />
          <Handle id="t-left" type="target" :position="Position.Left" />
          <Handle id="t-right" type="target" :position="Position.Right" />
          <Handle id="t-bot" type="target" :position="Position.Bottom" />
          <p class="node-title">{{ data.title }}</p>
          <p class="node-desc">{{ data.desc }}</p>
          <Handle id="s-bottom" type="source" :position="Position.Bottom" />
          <Handle id="s-left" type="source" :position="Position.Left" />
          <Handle id="s-right" type="source" :position="Position.Right" />
        </div>
      </template>
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { Background } from '@vue-flow/background'
import { Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import type { Edge, Node } from '@vue-flow/core'

/* 触屏手势标记 */
const isTouch = matchMedia('(hover: none), (pointer: coarse)').matches

/* 列位与泳道行位 */
const COLS = [0, 236, 472, 708]
const ROWS = [0, 150, 300, 450, 600]

const at = (col: number, row: number) => ({ x: COLS[col]!, y: ROWS[row]! })

/* 泳道名，标在该行入口一侧 */
const lane = (row: number, title: string, side: 'left' | 'right'): Node => ({
  id: `lane-${row}`,
  type: 'lane',
  position: { x: side === 'right' ? 902 : -118, y: ROWS[row]! + 28 },
  data: { title, side },
})

const nodes: Node[] = [
  lane(0, '前端 · 发起', 'left'),
  lane(1, '服务端 · 接入', 'right'),
  lane(2, 'Agent 循环', 'left'),
  lane(3, 'SSE 通道', 'right'),
  lane(4, '前端 · 渲染', 'left'),
  {
    id: 'input',
    type: 'stage',
    position: at(0, 0),
    data: { title: 'ChatInput', desc: '回车发送 · 附件本地' },
  },
  {
    id: 'store',
    type: 'stage',
    position: at(1, 0),
    data: { title: '会话 Store', desc: '轮次状态 · 三路并发' },
  },
  {
    id: 'api',
    type: 'stage',
    position: at(2, 0),
    data: { title: 'api/chat', desc: 'POST /chat/stream' },
  },
  {
    id: 'sse',
    type: 'stage',
    position: at(3, 0),
    data: { title: 'sseUtil', desc: 'fetch-event-source' },
  },
  {
    id: 'route',
    type: 'stage',
    position: at(3, 1),
    data: { title: 'chat_stream', desc: '请求校验 · 流式响应' },
  },
  {
    id: 'turn',
    type: 'stage',
    position: at(2, 1),
    data: { title: 'start_turn', desc: 'chat_thread · seq' },
  },
  {
    id: 'build',
    type: 'stage',
    position: at(1, 1),
    data: { title: '建图装配', desc: '每请求重建 · 挂检查点' },
  },
  {
    id: 'prompt',
    type: 'stage',
    position: at(0, 1),
    data: { title: '提示词组装', desc: '角色 + 规则 + 工具段' },
  },
  {
    id: 'middleware',
    type: 'stage',
    position: at(0, 2),
    data: { title: '中间件链', desc: '可见性过滤 · 工具事件' },
  },
  {
    id: 'model',
    type: 'stage',
    position: at(1, 2),
    data: { title: '模型调用', desc: '工厂选型 · 档位透传' },
  },
  {
    id: 'branch',
    type: 'stage',
    position: at(2, 2),
    data: { title: 'tool_calls 判定', desc: '有调用转工具节点' },
  },
  {
    id: 'tool',
    type: 'stage',
    position: at(3, 2),
    data: { title: '工具执行', desc: '检索后同轮再调用' },
  },
  {
    id: 'stream',
    type: 'stage',
    position: at(3, 3),
    data: { title: '事件双轨', desc: '边发事件 · 边写回段' },
  },
  {
    id: 'encode',
    type: 'stage',
    position: at(2, 3),
    data: { title: 'SSE 编码', desc: 'data: 一行一帧' },
  },
  {
    id: 'parse',
    type: 'stage',
    position: at(1, 3),
    data: { title: '逐帧解析', desc: 'JSON 帧 · done 判定' },
  },
  {
    id: 'dispatch',
    type: 'stage',
    position: at(0, 3),
    data: { title: '事件分发', desc: '正文·推理·工具·用量' },
  },
  {
    id: 'history',
    type: 'stage',
    position: at(0, 4),
    data: { title: '历史接口', desc: 'keyset 游标翻页' },
  },
  {
    id: 'aggregate',
    type: 'stage',
    position: at(1, 4),
    data: { title: '段落聚合', desc: '按 id 拼字归组' },
  },
  {
    id: 'handler',
    type: 'stage',
    position: at(2, 4),
    data: { title: '组件分发', desc: '按类型派子组件' },
  },
  {
    id: 'bubble',
    type: 'stage',
    position: at(3, 4),
    data: { title: '气泡渲染', desc: 'markdown · 逐字贴底' },
  },
]

const arrow = { type: MarkerType.ArrowClosed, width: 14, height: 14, color: '#a78bfa' }

/* 连线：蛇形主链 + 工具回环 */
const edges: Edge[] = [
  {
    id: 'input-store',
    source: 'input',
    target: 'store',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'store-api',
    source: 'store',
    target: 'api',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'api-sse',
    source: 'api',
    target: 'sse',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'sse-route',
    source: 'sse',
    target: 'route',
    sourceHandle: 's-bottom',
    targetHandle: 't-top',
  },
  {
    id: 'route-turn',
    source: 'route',
    target: 'turn',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'turn-build',
    source: 'turn',
    target: 'build',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'build-prompt',
    source: 'build',
    target: 'prompt',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'prompt-middleware',
    source: 'prompt',
    target: 'middleware',
    sourceHandle: 's-bottom',
    targetHandle: 't-top',
  },
  {
    id: 'middleware-model',
    source: 'middleware',
    target: 'model',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'model-branch',
    source: 'model',
    target: 'branch',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'branch-tool',
    source: 'branch',
    target: 'tool',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'tool-stream',
    source: 'tool',
    target: 'stream',
    sourceHandle: 's-bottom',
    targetHandle: 't-top',
  },
  {
    id: 'tool-model',
    source: 'tool',
    target: 'model',
    sourceHandle: 's-bottom',
    targetHandle: 't-bot',
  },
  {
    id: 'stream-encode',
    source: 'stream',
    target: 'encode',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'encode-parse',
    source: 'encode',
    target: 'parse',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'parse-dispatch',
    source: 'parse',
    target: 'dispatch',
    sourceHandle: 's-left',
    targetHandle: 't-right',
  },
  {
    id: 'dispatch-aggregate',
    source: 'dispatch',
    target: 'aggregate',
    sourceHandle: 's-bottom',
    targetHandle: 't-top',
  },
  {
    id: 'history-aggregate',
    source: 'history',
    target: 'aggregate',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'aggregate-handler',
    source: 'aggregate',
    target: 'handler',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
  {
    id: 'handler-bubble',
    source: 'handler',
    target: 'bubble',
    sourceHandle: 's-right',
    targetHandle: 't-left',
  },
].map((edge) => ({ ...edge, animated: true, markerEnd: arrow, type: 'smoothstep' as const }))
</script>

<style scoped>
/* 画布容器显式宽高 */
.flow-diagram {
  width: 100%;
  height: calc(100vh - 180px);
  min-height: 420px;
  max-height: 640px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fff;
}
@supports (height: 100dvh) {
  .flow-diagram {
    height: calc(100dvh - 180px);
  }
}
.flow-canvas {
  background: none;
}
/* 触屏手势 */
.flow-canvas.is-touch {
  touch-action: none;
}
.flow-node {
  position: relative;
  width: 180px;
  padding: 9px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background: #fff;
  text-align: left;
}
.node-title {
  margin: 0;
  color: #24292f;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
}
.node-desc {
  margin: 4px 0 0;
  color: #8a9099;
  font-size: 13.5px;
  line-height: 1.4;
}
.lane-label {
  margin: 0;
  padding-left: 9px;
  border-left: 3px solid #c4b5fd;
  color: #7c3aed;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
  white-space: nowrap;
}
.lane-label.is-right {
  padding-left: 0;
  padding-right: 9px;
  border-left: 0;
  border-right: 3px solid #c4b5fd;
}
:deep(.vue-flow__handle) {
  opacity: 0;
}
:deep(.vue-flow__edge-path) {
  stroke: #a78bfa;
  stroke-width: 1.4;
}
@media (prefers-reduced-motion: reduce) {
  :deep(.vue-flow__edge.animated path) {
    animation: none;
  }
}
</style>
