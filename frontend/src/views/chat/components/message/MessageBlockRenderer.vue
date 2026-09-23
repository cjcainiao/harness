<template>
  <component :is="blockComponent" v-if="blockComponent" :block="block" />
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import MessageTextBlock from './MessageTextBlock.vue'
import type { MessageBlock } from './messageTypes'

const props = defineProps<{ block: MessageBlock }>()

// 推理、工具调用和自定义事件的组件后续在这里注册
const blockComponents: Partial<Record<MessageBlock['type'], Component>> = {
  text: MessageTextBlock,
}

const blockComponent = computed(() => blockComponents[props.block.type])
</script>

<style scoped></style>
