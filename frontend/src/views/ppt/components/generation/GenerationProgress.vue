<!--PPT 生成进度区-->
<template>
  <section class="generation-progress" aria-labelledby="progress-heading">
    <div class="card-heading">
      <div class="heading-icon"><WandSparkles :size="17" :stroke-width="1.8" /></div>
      <div class="heading-copy">
        <h3 id="progress-heading">生成进度</h3>
        <p>从资料到页面，步骤清晰可见。</p>
      </div>
      <span class="card-step">STEP 02</span>
    </div>
    <div class="progress-body">
      <div class="progress-caption"><span>等待开始</span><strong>0%</strong></div>
      <div
        class="progress-track"
        role="progressbar"
        aria-label="生成进度"
        aria-valuenow="0"
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <span />
      </div>
      <ol class="step-list">
        <li v-for="(step, index) in steps" :key="step">
          <span class="step-mark">{{ index + 1 }}</span>
          <span>{{ step }}</span>
          <span class="step-state">待开始</span>
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup lang="ts">
import { WandSparkles } from 'lucide-vue-next'

const steps = ['整理资料与主题', '生成内容大纲', '绘制演示页面']
</script>

<style scoped>
.generation-progress {
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
.progress-body {
  padding: 20px;
}
.progress-caption {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #929a9a;
  font-size: 11px;
}
.progress-caption strong {
  color: #727d75;
  font-weight: 650;
}
.progress-track {
  height: 5px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 10px;
  background: #eef1ef;
}
.progress-track span {
  display: block;
  width: 0;
  height: 100%;
}
.step-list {
  display: grid;
  gap: 12px;
  margin: 19px 0 0;
  padding: 0;
  list-style: none;
}
.step-list li {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #6d7675;
  font-size: 11px;
}
.step-mark {
  display: grid;
  width: 20px;
  height: 20px;
  flex: none;
  place-items: center;
  border: 1px solid #e9edeb;
  border-radius: 50%;
  color: #adb7b0;
  font-size: 10px;
}
.step-state {
  margin-left: auto;
  color: #afb5b7;
  font-size: 10px;
}
@media (max-width: 375px) {
  .card-heading,
  .progress-body {
    padding: 16px;
  }
}
</style>
