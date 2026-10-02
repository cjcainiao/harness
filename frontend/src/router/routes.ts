// 汇总路由
import type { RouteRecordRaw } from 'vue-router'

import homeRoutes from './modules/home'
import chatRoutes from './modules/chat'
import configRoutes from './modules/config'

const routes: RouteRecordRaw[] = [...homeRoutes, ...chatRoutes, ...configRoutes]

export default routes
