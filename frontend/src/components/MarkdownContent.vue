<template>
  <div class="markdown-content" v-html="renderedHtml" />
</template>

<script setup lang="ts">
import MarkdownIt from 'markdown-it'
import { computed } from 'vue'

const props = defineProps<{ content: string }>()

// 正文来自消息事件，禁用原始 HTML，避免将其作为页面元素插入
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
const renderedHtml = computed(() => markdown.render(props.content))
</script>

<style scoped>
.markdown-content {
  min-width: 0;
  color: #292d32;
  font-size: 14px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.markdown-content :deep(p),
.markdown-content :deep(ul),
.markdown-content :deep(ol),
.markdown-content :deep(blockquote),
.markdown-content :deep(pre),
.markdown-content :deep(table) {
  margin: 0 0 1em;
}
.markdown-content :deep(> :last-child) {
  margin-bottom: 0;
}
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin: 1.25em 0 0.55em;
  color: #202327;
  font-weight: 600;
  line-height: 1.4;
}
.markdown-content :deep(h1) {
  font-size: 1.45em;
}
.markdown-content :deep(h2) {
  font-size: 1.3em;
}
.markdown-content :deep(h3) {
  font-size: 1.15em;
}
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  font-size: 1em;
}
.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 1.6em;
}
.markdown-content :deep(ul) {
  list-style: disc;
}
.markdown-content :deep(ol) {
  list-style: decimal;
}
.markdown-content :deep(li + li) {
  margin-top: 0.35em;
}
.markdown-content :deep(li > ul),
.markdown-content :deep(li > ol) {
  margin-top: 0.35em;
  margin-bottom: 0;
}
.markdown-content :deep(a) {
  color: #3369aa;
  text-decoration: underline;
  text-underline-offset: 2px;
}
.markdown-content :deep(a:focus-visible) {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
@media (hover: hover) {
  .markdown-content :deep(a:hover) {
    color: #1e4d87;
  }
}
.markdown-content :deep(blockquote) {
  padding: 2px 0 2px 12px;
  border-left: 3px solid #d6dce4;
  color: #65707b;
}
.markdown-content :deep(code) {
  padding: 0.15em 0.35em;
  border-radius: 4px;
  background: #f1f3f5;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 0.9em;
}
.markdown-content :deep(pre) {
  max-width: 100%;
  padding: 12px 14px;
  overflow-x: auto;
  border: 1px solid #e9ebee;
  border-radius: 8px;
  background: #f7f8fa;
}
.markdown-content :deep(pre code) {
  padding: 0;
  background: transparent;
  font-size: 13px;
  line-height: 1.55;
}
.markdown-content :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}
.markdown-content :deep(th),
.markdown-content :deep(td) {
  padding: 7px 10px;
  border: 1px solid #e1e5e9;
  text-align: left;
}
.markdown-content :deep(th) {
  background: #f7f8fa;
  font-weight: 600;
}
.markdown-content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}
.markdown-content :deep(hr) {
  margin: 1.2em 0;
  border: 0;
  border-top: 1px solid #e8e9eb;
}
</style>
