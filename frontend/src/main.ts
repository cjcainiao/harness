import { createApp } from 'vue'
import { createPinia } from 'pinia'
// 注册ElementPlus
import ElementPlus from 'element-plus'

import App from './App.vue'
import router from './router'
// 全局初始化样式
import './assets/css/init.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')
