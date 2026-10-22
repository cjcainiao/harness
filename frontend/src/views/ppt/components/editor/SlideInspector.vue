<!--PPT 内容编辑区-->
<template>
  <aside class="slide-inspector" aria-labelledby="inspector-heading">
    <div class="panel-heading">
      <h3 id="inspector-heading">内容编辑</h3>
      <Settings2 :size="15" :stroke-width="1.8" />
    </div>
    <div class="inspector-body">
      <div class="selection-icon"><MousePointer2 :size="19" :stroke-width="1.6" /></div>
      <strong>选择页面中的内容</strong>
      <p>选中标题、文字或图片后，编辑选项将在这里显示。</p>
    </div>
    <div class="inspector-footer">
      <span class="footer-line" /><span class="footer-line short" />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { MousePointer2, Settings2 } from 'lucide-vue-next'
</script>

<style scoped>
.slide-inspector {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e8e9eb;
  border-radius: 10px;
  background: #fff;
}
.panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 49px;
  padding: 0 16px;
  border-bottom: 1px solid #f0f1f0;
  color: #9ca6a0;
}
h3 {
  color: #3d4346;
  font-size: 12px;
  font-weight: 650;
}
.inspector-body {
  display: flex;
  min-height: 180px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 14px;
  text-align: center;
}
.selection-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid #e6ece7;
  border-radius: 10px;
  background: #fafcfb;
  color: #90a195;
}
.inspector-body strong {
  margin-top: 14px;
  color: #69736c;
  font-size: 11px;
  font-weight: 620;
}
.inspector-body p {
  max-width: 172px;
  margin-top: 6px;
  color: #a4aba7;
  font-size: 10px;
  line-height: 1.6;
}
.inspector-footer {
  display: grid;
  gap: 8px;
  padding: 15px 18px;
  border-top: 1px solid #f1f2f1;
}
.footer-line {
  width: 100%;
  height: 5px;
  border-radius: 5px;
  background: #f0f2f0;
}
.footer-line.short {
  width: 60%;
}
</style>
