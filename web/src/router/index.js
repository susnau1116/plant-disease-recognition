import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue'), meta: { title: '首页识别' } },
  { path: '/result', name: 'result', component: () => import('../views/ResultView.vue'), meta: { title: '识别结果' } },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/KnowledgeView.vue'), meta: { title: '病害知识库' } },
  { path: '/knowledge/:className', name: 'disease-detail', component: () => import('../views/DiseaseDetailView.vue'), meta: { title: '病害详情' } },
  { path: '/consult', name: 'consult', component: () => import('../views/ConsultView.vue'), meta: { title: '专家咨询' } },
  { path: '/messages', name: 'messages', component: () => import('../views/MessagesView.vue'), meta: { title: '留言管理' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 农作物病害识别与防治系统` : '农作物病害识别与防治系统'
})

export default router
