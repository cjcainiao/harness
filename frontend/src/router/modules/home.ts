// home 模块路由
import type { RouteRecordRaw } from 'vue-router'

const homeRoutes: RouteRecordRaw[] = [
  // 旧入口统一重定向到首页
  { path: '/index', redirect: '/' },
  { path: '/index.html', redirect: '/' },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/home/LayoutView.vue'),
    children: [
      {
        path: '',
        name: 'home-index',
        component: () => import('@/views/home/IndexView.vue'),
      },
    ],
  },
]

export default homeRoutes
