<!--PPT 导出面板-->
<template>
  <section class="export-panel" aria-labelledby="export-heading">
    <div class="panel-heading">
      <h3 id="export-heading">检查与导出</h3>
      <Download :size="15" :stroke-width="1.8" />
    </div>
    <div class="export-body">
      <div class="check-row">
        <span class="check-mark"><Check :size="12" :stroke-width="2" /></span> 页面尺寸
        <span>16:9</span>
      </div>
      <div class="check-row"><span class="pending-mark" /> 内容检查 <span>待生成</span></div>
      <button type="button" disabled><Download :size="14" :stroke-width="1.8" /> 导出 PPTX</button>
      <p>演示文稿生成后即可检查并导出。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Check, Download } from 'lucide-vue-next'
</script>

<style scoped>
.export-panel {
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
.export-body {
  padding: 17px 16px;
}
.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 28px;
  color: #78807b;
  font-size: 10px;
}
.check-row > span:last-child {
  margin-left: auto;
  color: #a3aaa6;
}
.check-mark,
.pending-mark {
  display: grid;
  width: 17px;
  height: 17px;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: #edf5ee;
  color: #719879;
}
.pending-mark {
  border: 1px solid #e2e7e4;
  background: #f8faf8;
}
.export-body button {
  display: flex;
  width: 100%;
  min-height: 35px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 14px;
  border: 0;
  border-radius: 7px;
  background: #d0d3d4;
  color: #fff;
  cursor: not-allowed;
  font-size: 11px;
  font-weight: 600;
}
.export-body p {
  margin-top: 9px;
  color: #abb1af;
  font-size: 10px;
  line-height: 1.5;
  text-align: center;
}
@media (any-pointer: coarse) {
  .export-body button {
    min-height: 44px;
  }
}
</style>
