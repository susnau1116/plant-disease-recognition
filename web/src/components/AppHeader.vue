<template>
  <header class="header">
    <div class="container header-inner">
      <router-link to="/" class="brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none">
            <path d="M19 4C11 4 5 8.5 5 15c0 2 .6 3.6 1.4 4.8C7.6 12.4 11.5 8.9 17 7.5c-4.6 2.4-8.2 6-9.7 12.2.9.2 1.8.3 2.7.3 7.5 0 11.5-5.5 11.5-12.5 0-1.3-.2-2.4-.5-3.5z" fill="currentColor"/>
          </svg>
        </span>
        <span class="brand-text">
          <strong>农作物病害识别与防治系统</strong>
          <small>Plant Disease Recognition &amp; Treatment</small>
        </span>
      </router-link>
      <nav class="nav">
        <router-link to="/" exact-active-class="active">首页识别</router-link>
        <router-link to="/knowledge" active-class="active">病害知识库</router-link>
        <router-link to="/consult" active-class="active">专家咨询</router-link>
        <router-link to="/messages" active-class="active">留言管理</router-link>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  height: 68px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--green-900);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: var(--green-100);
  color: var(--green-700);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.brand-text strong {
  font-size: 17px;
}

.brand-text small {
  color: var(--ink-3);
  font-size: 11px;
  letter-spacing: 0.4px;
}

.nav {
  display: flex;
  gap: 6px;
}

.nav a {
  padding: 8px 16px;
  border-radius: 999px;
  color: var(--ink-2);
  font-size: 15px;
  font-weight: 600;
  transition: background 0.2s, color 0.2s;
}

.nav a:hover {
  background: var(--green-100);
  color: var(--green-900);
}

.nav a.active {
  background: var(--green-700);
  color: #fff;
}
</style>
