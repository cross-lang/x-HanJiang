import { createApp } from 'vue'
import { createPinia } from 'pinia'
// 按需引入：基础样式（CSS 变量/重置）+ 命令式服务样式
import 'element-plus/theme-chalk/base.css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
import 'element-plus/es/components/loading/style/css'
import App from './App.vue'
import router from './router'
import { setupIcons } from './plugins/icons'

const app = createApp(App)

setupIcons(app)

app.use(createPinia())
app.use(router)
app.mount('#app')
