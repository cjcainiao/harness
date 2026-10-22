<!--PPT 内容块示例-->
<template>
  <div class="block-renderer">
    <div class="slide-copy">
      <span class="slide-eyebrow">{{ eyebrow }} · 2026</span>
      <strong>{{ title }}</strong>
      <span class="slide-rule" />
      <p>{{ summary }}</p>
    </div>
    <div class="slide-decoration" aria-hidden="true">
      <span class="deco-card deco-back" />
      <span class="deco-card deco-front"><i /><i /><i /></span>
    </div>
    <span class="slide-corner">01 / 04</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; summary: string; eyebrow: string }>()
</script>

<style scoped>
.block-renderer {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  padding: 8% 9%;
}
.slide-copy {
  position: relative;
  z-index: 1;
  width: 64%;
}
.slide-eyebrow {
  display: block;
  margin-bottom: 7%;
  color: var(--slide-accent);
  font-size: clamp(6px, 0.8vw, 10px);
  font-weight: 700;
  letter-spacing: 0.14em;
}
.slide-copy strong {
  display: block;
  color: var(--slide-ink);
  font-size: clamp(15px, 2.65vw, 35px);
  font-weight: 730;
  letter-spacing: -0.055em;
  line-height: 1.22;
}
.slide-rule {
  display: block;
  width: 13%;
  height: 2px;
  margin: 8% 0 4%;
  background: var(--slide-accent);
}
.slide-copy p {
  max-width: 85%;
  color: var(--slide-muted);
  font-size: clamp(6px, 0.9vw, 11px);
  line-height: 1.55;
}
.slide-decoration {
  position: absolute;
  right: 7%;
  bottom: 15%;
  width: 28%;
  height: 55%;
}
.deco-card {
  position: absolute;
  display: block;
  width: 72%;
  height: 74%;
  border: 1px solid rgb(255 255 255 / 80%);
  border-radius: 3%;
  box-shadow: 0 10px 20px rgb(41 72 48 / 9%);
}
.deco-back {
  top: 4%;
  right: 0;
  transform: rotate(12deg);
  background: var(--slide-card);
}
.deco-front {
  bottom: 0;
  left: 0;
  padding: 18% 13%;
  transform: rotate(-7deg);
  background: #fff;
}
.deco-front i {
  display: block;
  height: 5%;
  margin-bottom: 12%;
  border-radius: 2px;
  background: #bbd3be;
}
.deco-front i:nth-child(2) {
  width: 85%;
  background: #d5e3d5;
}
.deco-front i:nth-child(3) {
  width: 60%;
  background: #d5e3d5;
}
.slide-corner {
  position: absolute;
  right: 9%;
  bottom: 8%;
  color: var(--slide-muted);
  font-size: clamp(6px, 0.8vw, 10px);
  letter-spacing: 0.08em;
}
@media (max-width: 720px) {
  .slide-eyebrow {
    font-size: clamp(5px, 1.6vw, 8px);
  }
  .slide-copy strong {
    font-size: clamp(12px, 4vw, 22px);
  }
  .slide-copy p {
    font-size: clamp(5px, 1.65vw, 8px);
  }
  .slide-corner {
    font-size: 6px;
  }
}
</style>
