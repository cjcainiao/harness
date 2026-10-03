<!--Markdown 渲染组件-->
<template>
  <div class="markdown-content" v-html="renderedHtml" />
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const props = defineProps<{ content: string }>()

// 禁用原始 HTML，避免内容作为页面元素插入
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
const renderedHtml = computed(() => markdown.render(props.content))
</script>
