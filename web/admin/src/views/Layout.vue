<template>
  <el-container style="height: 100vh">
    <el-aside
      :width="isCollapsed ? '64px' : '200px'"
      style="background: #ffffff; border-right: 1px solid #e4e7ed; position: relative; transition: width 0.25s ease; overflow: hidden"
    >
      <div
        class="app-title"
        :title="isCollapsed ? '点击展开菜单' : '点击收起菜单'"
        @click="toggleMenu"
      >
        <img
          src="/logo-icon.png"
          class="app-logo"
          :style="{ width: isCollapsed ? '32px' : '36px', height: isCollapsed ? '32px' : '36px' }"
          alt="汉江管理系统"
        />
        <span v-if="!isCollapsed" class="app-name">汉江管理系统</span>
      </div>
      <el-menu
        :default-active="$route.path"
        background-color="#ffffff"
        text-color="#5a5e66"
        active-text-color="#409eff"
        router
        :collapse="isCollapsed"
        :collapse-transition="false"
      >
        <template v-for="menu in menus" :key="menu.id">
          <!-- 目录：有子菜单 -->
          <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="String(menu.id)">
            <template #title>
              <el-icon><component :is="menu.icon" /></el-icon>
              <span>{{ menu.title }}</span>
            </template>
            <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
              <el-icon><component :is="child.icon" /></el-icon>
              <span>{{ child.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <!-- 菜单：直接可点击 -->
          <el-menu-item v-else :index="menu.path">
            <el-icon><component :is="menu.icon" /></el-icon>
            <span>{{ menu.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; justify-content: flex-end; align-items: center">
        <GlobalSearch />
        <NotificationBell />
        <div class="ai-btn" @click="openAiDrawer">
          <div class="ai-entry">
            <el-icon :size="18"><MagicStick /></el-icon>
            <span>AI 助手</span>
          </div>
        </div>
        <el-dropdown @command="handleCommand">
          <span style="cursor: pointer; display: flex; align-items: center; gap: 10px">
            <el-avatar :size="36" style="background: #79bbff">
              {{ (userStore.userInfo?.name || userStore.userInfo?.username || 'U').charAt(0) }}
            </el-avatar>
            <div style="line-height: 1.4">
              <div style="font-weight: 500; color: #333">{{ userStore.userInfo?.name || userStore.userInfo?.username || '用户' }}</div>
              <div style="font-size: 12px; color: #999">{{ userStore.userInfo?.email || '' }}</div>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile"><el-icon style="margin-right: 8px"><User /></el-icon>个人中心</el-dropdown-item>
              <el-dropdown-item divided>
                <a href="https://github.com/cross-lang/x-HanJiang" target="_blank" style="display: flex; align-items: center; gap: 8px; color: inherit; text-decoration: none; line-height: 32px">
                  <el-icon><Link /></el-icon> GitHub
                </a>
              </el-dropdown-item>
              <el-dropdown-item>
                <a href="https://gitee.com/cross-lang/x-HanJiang" target="_blank" style="display: flex; align-items: center; gap: 8px; color: inherit; text-decoration: none; line-height: 32px">
                  <el-icon><Star /></el-icon> Gitee
                </a>
              </el-dropdown-item>
              <el-dropdown-item divided command="logout"><el-icon style="margin-right: 8px"><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background: #f0f2f5; padding: 0; display: flex; flex-direction: column">
        <div v-if="!isHome" style="background: #fff; padding: 12px 20px; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 12px">
          <el-button text @click="$router.push('/dashboard')">
            <el-icon style="margin-right: 4px"><Back /></el-icon>返回首页
          </el-button>
          <el-divider direction="vertical" />
          <span style="color: #606266; font-size: 14px">{{ pageTitle }}</span>
        </div>
        <div style="flex: 1; padding: 20px">
          <router-view />
        </div>
        <div class="app-footer">
          Copyright © {{ currentYear }} 汉江管理系统 All Rights Reserved
        </div>
      </el-main>
    </el-container>

    <!-- AI 助手聊天弹窗 -->
    <el-drawer v-model="aiVisible" title="AI 助手" size="420px" direction="rtl">
      <div style="display: flex; flex-direction: column; height: 100%">
        <div style="flex: 1; overflow-y: auto; padding: 12px; background: #f8f9fb; border-radius: 8px; margin-bottom: 12px">
          <div v-if="aiMessages.length === 0" style="text-align: center; color: #666; padding: 24px 12px">
            <el-icon size="40" color="#409eff"><MagicStick /></el-icon>
            <p style="margin: 12px 0 4px; font-size: 15px; font-weight: 600; color: #333">你好！我是小江，汉江管理系统的 AI 导览助手</p>
            <p style="font-size: 13px; color: #909399; margin-bottom: 12px">不熟悉系统怎么操作？直接问我，我可以教你并帮你跳转到对应页面：</p>
            <div style="text-align: left; font-size: 14px; line-height: 1.9; color: #409eff; background: #ecf5ff; border-radius: 8px; padding: 10px 14px">
              <div>· 怎么添加用户？</div>
              <div>· 帮我跳到权限管理</div>
              <div>· 用户列表在哪里？</div>
              <div>· 怎么修改我的个人资料？</div>
            </div>
          </div>
          <div
            v-for="(msg, idx) in aiMessages"
            :key="idx"
            style="margin-bottom: 12px; display: flex; flex-direction: column"
            :style="msg.role === 'user' ? 'align-items: flex-end' : 'align-items: flex-start'"
          >
            <div
              :style="
                msg.role === 'user'
                  ? 'background: #409eff; color: #fff; padding: 8px 12px; border-radius: 8px; max-width: 80%; white-space: pre-wrap; word-break: break-word'
                  : 'background: #fff; color: #333; border: 1px solid #e4e7ed; padding: 8px 12px; border-radius: 8px; max-width: 80%; white-space: pre-wrap; word-break: break-word'
              "
            >
              <span v-if="msg.loading && !msg.content" class="ai-typing">正在思考<span class="ai-dot">…</span></span>
              <template v-else>{{ msg.content }}</template>
            </div>
            <div
              v-if="msg.role === 'assistant' && msg.messageId != null"
              style="display: flex; gap: 2px; margin-top: 2px"
            >
              <el-button
                text
                size="small"
                :type="msg.feedback === 'up' ? 'primary' : 'info'"
                :disabled="msg.feedback !== null"
                @click="submitAiFeedback(msg, true)"
              >
                <el-icon :size="13"><Select /></el-icon>&nbsp;有帮助
              </el-button>
              <el-button
                text
                size="small"
                :type="msg.feedback === 'down' ? 'danger' : 'info'"
                :disabled="msg.feedback !== null"
                @click="submitAiFeedback(msg, false)"
              >
                <el-icon :size="13"><Close /></el-icon>&nbsp;没帮助
              </el-button>
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 8px">
          <el-input
            v-model="aiInput"
            placeholder="输入你的问题..."
            :disabled="aiLoading"
            @keyup.enter="sendAiMessage"
          />
          <el-button type="primary" :loading="aiLoading" :disabled="aiLoading" @click="sendAiMessage">发送</el-button>
        </div>
      </div>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import GlobalSearch from '@/components/GlobalSearch.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import {
  chatSSE,
  getConversationMessages,
  submitFeedback,
  type MessageItem,
} from '@/api/assistant'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const currentYear = new Date().getFullYear()

// 当前是否为首页（/dashboard 或根路径 /）
const isHome = computed(() => route.path === '/dashboard' || route.path === '/')

const aiVisible = ref(false)
const aiInput = ref('')
const aiLoading = ref(false)
// 最近会话ID（续聊上下文；null 表示新会话，首轮由后端自动创建）
const aiConversationId = ref<number | null>(
  Number(localStorage.getItem('ai_conversation_id')) || null,
)
// 消息：user / assistant（assistant 支持 loading 占位、messageId 反馈定位、feedback 选中态）
interface AiMsg {
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
  messageId?: number | null
  feedback?: 'up' | 'down' | null
}
const aiMessages = ref<AiMsg[]>([])

/** 打开 AI 助手抽屉：恢复最近会话的历史消息 */
async function openAiDrawer() {
  aiVisible.value = true
  if (aiMessages.value.length > 0) return
  if (aiConversationId.value === null) return // 无会话：显示欢迎引导语
  try {
    const res: any = await getConversationMessages(aiConversationId.value)
    const items: MessageItem[] = res?.data ?? []
    aiMessages.value = items.map((item) => ({
      role: item.role === 'user' ? 'user' : 'assistant',
      content: item.content,
      messageId: item.id,
      feedback: null,
    }))
  } catch {
    // 加载历史失败（如会话已失效）：重置会话，从欢迎引导开始
    aiConversationId.value = null
    localStorage.removeItem('ai_conversation_id')
  }
}

async function sendAiMessage() {
  const text = aiInput.value.trim()
  if (!text || aiLoading.value) return
  aiInput.value = ''
  aiMessages.value.push({ role: 'user', content: text })
  // 助手占位消息：SSE 期间流式填充
  const assistantMsg: AiMsg = { role: 'assistant', content: '', loading: true, messageId: null, feedback: null }
  aiMessages.value.push(assistantMsg)
  aiLoading.value = true
  try {
    await chatSSE(aiConversationId.value, text, {
      onThinking: () => {
        // 可在此透出"正在思考"；默认由 loading 占位展示
      },
      onToken: (chunk) => {
        assistantMsg.content += chunk
      },
      onNavigate: (path) => {
        // 跳转指令：执行路由跳转并关闭抽屉（剩余流式文本不再展示）
        router.push(path)
        aiVisible.value = false
      },
      onDenied: () => {
        // 越权拒绝：模型随后会流式说明，无需额外动作
      },
      onError: (message) => {
        assistantMsg.content = message || '服务异常，请稍后再试'
      },
      onDone: ({ conversationId, messageId }) => {
        if (conversationId !== null && conversationId !== aiConversationId.value) {
          aiConversationId.value = conversationId
          localStorage.setItem('ai_conversation_id', String(conversationId))
        }
        assistantMsg.loading = false
        assistantMsg.messageId = messageId // 供 👍👎 反馈定位
      },
    })
  } catch (err: any) {
    assistantMsg.loading = false
    assistantMsg.content = err?.message || '网络异常，请稍后再试'
  } finally {
    aiLoading.value = false
  }
}

/** 提交 👍👎 反馈（成功后锁定，防止重复提交） */
async function submitAiFeedback(msg: AiMsg, positive: boolean) {
  if (msg.feedback !== null || aiConversationId.value === null || msg.messageId == null) return
  try {
    await submitFeedback({
      conversation_id: aiConversationId.value,
      message_id: msg.messageId,
      positive,
    })
    msg.feedback = positive ? 'up' : 'down'
  } catch {
    // 失败提示由请求拦截器统一处理
  }
}

// 左侧菜单折叠状态（持久化到 localStorage）
const isCollapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')

function toggleMenu() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar_collapsed', isCollapsed.value ? '1' : '0')
}

const menus = computed(() => userStore.menus)

const pageTitle = computed(() => {
  // 从菜单树里找当前路由对应的标题
  const findTitle = (list: any[], path: string): string => {
    for (const item of list) {
      if (item.path === path) return item.title
      if (item.children) {
        const found = findTitle(item.children, path)
        if (found) return found
      }
    }
    return ''
  }
  const titleMap: Record<string, string> = { '/profile': '个人中心' }
  return findTitle(menus.value, route.path) || titleMap[route.path] || route.path
})

onMounted(async () => {
  try {
    await userStore.fetchUserInfo()
    await userStore.fetchMenus()
  } catch {
    router.push('/login')
  }
})

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #303133;
  padding: 16px 0;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition: color 0.2s ease, background-color 0.2s ease;
}
.app-logo {
  border-radius: 8px;
  flex-shrink: 0;
}
.app-name {
  line-height: 1;
}
.app-title:hover {
  color: #409eff;
  background-color: #f5f7fa;
}
.ai-btn {
  margin-right: 24px;
  cursor: pointer;
}
.ai-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
  transition: all 0.2s ease;
}
.ai-entry:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.45);
  filter: brightness(1.06);
}
.ai-typing {
  color: #909399;
  font-size: 13px;
}
.ai-dot {
  display: inline-block;
  animation: ai-blink 1s infinite steps(2, start);
}
@keyframes ai-blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.2;
  }
}
.app-footer {
  flex-shrink: 0;
  text-align: center;
  padding: 12px 0 20px;
  color: #909399;
  font-size: 12px;
  user-select: none;
}
</style>
