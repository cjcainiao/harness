<!--PPT 大纲编辑区-->
<template>
  <section class="outline-editor" aria-labelledby="outline-heading">
    <div class="card-heading">
      <div class="heading-icon"><ListTree :size="17" :stroke-width="1.8" /></div>
      <div class="heading-copy">
        <h3 id="outline-heading">内容大纲</h3>
        <p>确定每一页要讲什么，让表达更有条理。</p>
      </div>
      <span class="card-step">STEP 01</span>
    </div>
    <ol class="outline-list" aria-label="示例大纲">
      <li v-for="(item, index) in sections" :key="item">
        <span class="item-number">{{ String(index + 1).padStart(2, '0') }}</span>
        <span class="item-title">{{ item }}</span>
        <span class="sample-label">示例</span>
      </li>
    </ol>
    <div class="card-footer"><span class="footer-dot" /> 生成大纲后可在这里调整页面顺序与内容</div>
  </section>
</template>

<script setup lang="ts">
import { ListTree } from 'lucide-vue-next'

const sections = ['封面与核心主题', '背景与现状', '方案与重点', '总结与下一步']
</script>

<style scoped>
.outline-editor {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e8e9eb;
  border-radius: 11px;
  background: #fff;
}
.card-heading {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 19px 20px;
  border-bottom: 1px solid #f0f1f0;
}
.heading-icon {
  display: grid;
  width: 34px;
  height: 34px;
  flex: none;
  place-items: center;
  border: 1px solid #e6ede7;
  border-radius: 9px;
  background: #f7faf7;
  color: #638171;
}
.heading-copy {
  min-width: 0;
  flex: 1;
}
h3 {
  color: #343a3d;
  font-size: 13px;
  font-weight: 650;
}
.heading-copy p {
  margin-top: 4px;
  color: #9aa0a6;
  font-size: 10px;
  line-height: 1.4;
}
.card-step {
  color: #a8aeaf;
  font-size: 10px;
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.outline-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 18px 20px;
  list-style: none;
}
.outline-list li {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid #edf0ef;
  border-radius: 7px;
  background: #fcfdfc;
}
.item-number {
  color: #a8b7ad;
  font-size: 10px;
  font-weight: 650;
}
.item-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: #5a625d;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sample-label {
  color: #b5bbb6;
  font-size: 10px;
}
.card-footer {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 12px 20px;
  border-top: 1px solid #f0f1f0;
  color: #a1a7a9;
  font-size: 10px;
  line-height: 1.4;
}
.footer-dot {
  width: 5px;
  height: 5px;
  flex: none;
  border-radius: 50%;
  background: #c9d0cc;
}
@media (max-width: 375px) {
  .card-heading {
    padding: 16px;
  }
  .outline-list {
    padding: 16px;
  }
  .card-footer {
    padding: 12px 16px;
  }
}
</style>
