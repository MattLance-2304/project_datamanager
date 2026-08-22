import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

import MainLayout from './components/MainLayout.vue'
import LoginView from './views/LoginView.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { title: '仪表盘' } },
      { path: 'browse', component: () => import('./views/BrowseView.vue'), meta: { title: '数据浏览' } },
      { path: 'upload', component: () => import('./views/UploadView.vue'), meta: { title: '上传数据' } },
      { path: 'records/:id', component: () => import('./views/DetailView.vue'), meta: { title: '数据详情' } },
      { path: 'imagej/:id', component: () => import('./views/ImageJView.vue'), meta: { title: 'ImageJ 图像分析' } },
      { path: 'trash', component: () => import('./views/TrashView.vue'), meta: { title: '回收站' } },
      { path: 'admin', component: () => import('./views/AdminView.vue'), meta: { title: '系统管理', admin: true } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) return { path: '/login', query: { redirect: to.fullPath } }
  if (to.meta.admin && !auth.isAdmin) return { path: '/dashboard' }
  return true
})

export default router
