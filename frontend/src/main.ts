import { createApp } from 'vue'
import { createPinia } from 'pinia'
// 全局组件库
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
// 全局初始化样式
import './assets/css/init.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
