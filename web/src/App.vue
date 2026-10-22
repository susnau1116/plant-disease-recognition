<template>
  <div class="app">
    <AppHeader />
    <router-view />
    <footer class="footer">
      <div class="container footer-inner">
        <span>基于深度学习的农作物病害识别与防治系统</span>
        <span class="muted">模型 ResNet18 · 测试准确率 99.28% · 覆盖 38 类作物病害</span>
      </div>
    </footer>
  </div>
</template>

<script setup>
import AppHeader from './components/AppHeader.vue'
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.footer {
  margin-top: auto;
  border-top: 1px solid var(--line);
  background: #fff;
}

.footer-inner {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  justify-content: space-between;
  padding-top: 16px;
  padding-bottom: 16px;
  font-size: 13px;
}
</style>
