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
            <span>小江</span>
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

    <!-- 小江 AI 助手抽屉 -->
    <el-drawer v-model="aiVisible" size="420px" direction="rtl">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0 4px">
          <div style="display: flex; align-items: center; gap: 10px">
            <img
              :src="xiaoJiangLogo"
              alt="小江"
              style="width: 24px; height: 24px; object-fit: contain; flex-shrink: 0"
            />
            <span style="font-size: 16px; font-weight: 600">小江</span>
          </div>
          <el-button text size="small" @click="toggleConvPanel">
            <el-icon><ChatDotRound /></el-icon>&nbsp;{{ aiConvPanelVisible ? '收起会话' : '会话管理' }}
          </el-button>
        </div>
      </template>
      <div style="display: flex; flex-direction: column; height: 100%">
        <!-- 会话管理面板：点击「会话管理」嵌入聊天区上方，聊天记录顺势下移 -->
        <transition name="ai-panel">
        <div
          v-if="aiConvPanelVisible"
          class="ai-conv-panel"
          style="flex-shrink: 0; max-height: 264px; overflow-y: auto; border-radius: 12px; margin-bottom: 12px; padding: 12px 8px 8px"
        >
          <!-- 标题行 -->
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 0 2px 8px">
            <div style="display: flex; align-items: center; gap: 6px">
              <span style="width: 3px; height: 14px; border-radius: 2px; background: linear-gradient(180deg, #8b5cf6, #6366f1); display: inline-block"></span>
              <span style="font-size: 13px; color: #1f2329; font-weight: 600">会话列表</span>
            </div>
            <button
              type="button"
              style="display: inline-flex; align-items: center; gap: 2px; padding: 5px 10px; border: none; border-radius: 8px; cursor: pointer; color: #fff; font-size: 12px; font-weight: 500; background: linear-gradient(135deg, #8b5cf6, #6366f1); box-shadow: 0 1px 4px rgba(99, 102, 241, 0.3); transition: filter 0.15s; outline: none"
              @mouseenter="($event.target as HTMLElement).style.filter = 'brightness(1.08)'"
              @mouseleave="($event.target as HTMLElement).style.filter = 'none'"
              @click="createNewConversation"
            >
              <el-icon size="12"><Plus /></el-icon>&nbsp;新建会话
            </button>
          </div>
          <!-- 列表 -->
          <div v-if="aiConversations.length === 0" style="text-align: center; padding: 20px 8px">
            <el-icon size="28" color="#d5d3e8"><ChatDotRound /></el-icon>
            <p style="margin: 8px 0 0; font-size: 12px; color: #8f8f99">还没有会话，点击「新建会话」开始对话</p>
          </div>
          <div v-for="item in aiConversations" :key="item.id" style="margin-bottom: 2px">
            <!-- 分组标签：置顶 / 最近 -->
            <div
              v-if="item.is_pinned && item.id === pinnedConvs[0]?.id"
              class="ai-conv-group"
              style="padding: 6px 8px 3px; font-size: 11px; color: #9a9aa6; letter-spacing: 0.5px"
            >
              置顶
            </div>
            <div
              v-else-if="!item.is_pinned && item.id === recentConvs[0]?.id"
              class="ai-conv-group"
              style="padding: 6px 8px 3px; font-size: 11px; color: #9a9aa6; letter-spacing: 0.5px"
            >
              最近
            </div>
            <!-- 会话行：左侧当前会话高亮条 + 名称时间 + 置顶/删除 -->
            <div
              class="ai-conv-row"
              style="display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px; cursor: pointer"
              :style="
                item.id === aiConversationId
                  ? 'background: linear-gradient(90deg, rgba(139,92,246,0.06), rgba(99,102,241,0.02))'
                  : ''
              "
              @mouseenter="aiConvHoverId = item.id"
              @mouseleave="aiConvHoverId = null"
              @click="switchConversation(item.id)"
            >
              <div
                :style="
                  item.id === aiConversationId
                    ? 'width: 3px; height: 20px; border-radius: 2px; background: linear-gradient(180deg, #8b5cf6, #6366f1); flex-shrink: 0'
                    : 'width: 3px; height: 20px; flex-shrink: 0'
                "
              ></div>
              <div style="flex: 1; min-width: 0">
                <div style="font-size: 13px; color: #333; white-space: nowrap; overflow: hidden; text-overflow: ellipsis">
                  {{ convTitle(item) }}
                </div>
                <div style="font-size: 11px; color: #a3a3ad; margin-top: 2px">{{ convTime(item) }}</div>
              </div>
              <div style="display: flex; align-items: center; gap: 2px; flex-shrink: 0">
                <el-icon
                  :color="item.is_pinned ? '#8b5cf6' : '#b8b8c2'"
                  :title="item.is_pinned ? '取消置顶' : '置顶'"
                  style="cursor: pointer; padding: 3px; border-radius: 4px"
                  @mouseenter="($event.target as HTMLElement).style.color = '#8b5cf6'"
                  @mouseleave="($event.target as HTMLElement).style.color = item.is_pinned ? '#8b5cf6' : '#b8b8c2'"
                  @click.stop="togglePin(item)"
                >
                  <Top />
                </el-icon>
                <el-icon
                  title="删除"
                  style="cursor: pointer; padding: 3px; border-radius: 4px; color: #b8b8c2"
                  @mouseenter="($event.target as HTMLElement).style.color = '#f56c6c'"
                  @mouseleave="($event.target as HTMLElement).style.color = '#b8b8c2'"
                  @click.stop="deleteConversationItem(item.id)"
                >
                  <Delete />
                </el-icon>
              </div>
            </div>
          </div>
        </div>
        </transition>
        <!-- 聊天区 -->
        <div ref="chatScrollRef" style="flex: 1; overflow-y: auto; padding: 12px; background: #f8f9fb; border-radius: 8px; margin-bottom: 12px">
          <div v-if="aiMessages.length === 0" style="text-align: center; color: #666; padding: 24px 12px">
            <div
              style="width: 48px; height: 48px; margin: 0 auto 14px; border-radius: 14px; background: linear-gradient(135deg, #8b5cf6, #6366f1); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25); display: flex; align-items: center; justify-content: center"
            >
              <el-icon size="22" color="#fff"><MagicStick /></el-icon>
            </div>
            <p style="margin: 0 0 6px; font-size: 16px; font-weight: 600; color: #1f2329">你好！我是小江，汉江管理系统的 AI 导览助手</p>
            <p style="font-size: 13px; color: #909399; margin-bottom: 14px; line-height: 1.6">不熟悉系统怎么操作？直接问我，我可以教你并帮你跳转到对应页面：</p>
            <div style="text-align: left; font-size: 14px; line-height: 1.9; color: #409eff; background: #ecf5ff; border-radius: 8px; padding: 10px 14px">
              <div
                class="ai-quick-q"
                style="cursor: pointer; padding: 3px 6px; margin: 0 -6px; border-radius: 6px; transition: background 0.15s, transform 0.15s"
                @click="askQuickQuestion('怎么添加用户？')"
              >
                怎么添加用户？
              </div>
              <div
                class="ai-quick-q"
                style="cursor: pointer; padding: 3px 6px; margin: 0 -6px; border-radius: 6px; transition: background 0.15s, transform 0.15s"
                @click="askQuickQuestion('帮我跳到权限管理')"
              >
                帮我跳到权限管理
              </div>
              <div
                class="ai-quick-q"
                style="cursor: pointer; padding: 3px 6px; margin: 0 -6px; border-radius: 6px; transition: background 0.15s, transform 0.15s"
                @click="askQuickQuestion('用户列表在哪里？')"
              >
                用户列表在哪里？
              </div>
              <div
                class="ai-quick-q"
                style="cursor: pointer; padding: 3px 6px; margin: 0 -6px; border-radius: 6px; transition: background 0.15s, transform 0.15s"
                @click="askQuickQuestion('怎么修改我的个人资料？')"
              >
                怎么修改我的个人资料？
              </div>
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
        <!-- 输入区 -->
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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import GlobalSearch from '@/components/GlobalSearch.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import xiaoJiangLogo from '@/assets/xiaojiang-logo.png'
import {
  chatSSE,
  createConversation,
  deleteConversation,
  getConversationMessages,
  listConversations,
  pinConversation,
  submitFeedback,
  type ConversationItem,
  type MessageItem,
} from '@/api/assistant'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const currentYear = new Date().getFullYear()

// 当前是否为首页（/dashboard 或根路径 /）
const isHome = computed(() => route.path === '/dashboard' || route.path === '/')

const aiVisible = ref(false)
// 会话管理面板：展开时嵌入聊天区上方（不弹窗、不分栏）
const aiConvPanelVisible = ref(false)
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
// 会话管理：会话列表 / 会话管理弹层显隐
const aiConversations = ref<ConversationItem[]>([])
const aiConvHoverId = ref<number | null>(null)
// 会话分组：置顶优先，其余为最近
const pinnedConvs = computed(() => aiConversations.value.filter((c) => c.is_pinned))
const recentConvs = computed(() => aiConversations.value.filter((c) => !c.is_pinned))

// 聊天滚动：消息变化时自动滚到底部（用户主动上翻查看历史时暂停跟随）
const chatScrollRef = ref<HTMLElement | null>(null)

/** 当前视口是否处于消息列表底部附近（±80px 容差） */
function isNearBottom(): boolean {
  const el = chatScrollRef.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

/** 将消息列表滚动到底部（用户新消息、助手流式输出持续跟随） */
function scrollToBottom(): void {
  const el = chatScrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  aiMessages,
  async () => {
    if (isNearBottom()) {
      await nextTick()
      scrollToBottom()
    }
  },
  { deep: true },
)

/** 刷新当前用户的会话列表 */
async function refreshConversations() {
  try {
    const res: any = await listConversations()
    aiConversations.value = (res?.data ?? []) as ConversationItem[]
  } catch {
    aiConversations.value = []
  }
}

/** 会话列表标题：优先 AI 自动归纳的主题名，否则会话序号 */
function convTitle(item: ConversationItem): string {
  return item.title || `会话 #${item.id}`
}

/** 会话列表时间（MM-DD HH:mm） */
function convTime(item: ConversationItem): string {
  const d = new Date(item.updated_at)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 加载指定会话的历史消息并设为当前会话 */
async function loadConversation(id: number | null) {
  if (id === null) {
    aiMessages.value = []
    return
  }
  try {
    const res: any = await getConversationMessages(id)
    const items: MessageItem[] = res?.data ?? []
    aiMessages.value = items.map((item) => ({
      role: item.role === 'user' ? 'user' : 'assistant',
      content: item.content,
      messageId: item.id,
      feedback: null,
    }))
    aiConversationId.value = id
    localStorage.setItem('ai_conversation_id', String(id))
  } catch {
    // 加载历史失败（如会话已失效）：重置会话，从欢迎引导开始
    aiConversationId.value = null
    localStorage.removeItem('ai_conversation_id')
    aiMessages.value = []
  }
}

/** 切换会话 */
async function switchConversation(id: number) {
  aiConvPanelVisible.value = false
  await loadConversation(id)
}

/** 新建会话 */
async function createNewConversation() {
  aiConvPanelVisible.value = false
  try {
    const res: any = await createConversation()
    const conv: ConversationItem = res?.data
    if (conv?.id) {
      aiConversations.value = [conv, ...aiConversations.value.filter((c) => c.id !== conv.id)]
      await loadConversation(conv.id)
    }
  } catch {
    ElMessage.error('新建会话失败')
  }
}

/** 置顶 / 取消置顶会话（成功后刷新列表，后端按置顶优先排序） */
async function togglePin(item: ConversationItem) {
  try {
    await pinConversation(item.id, !item.is_pinned)
    await refreshConversations()
  } catch {
    ElMessage.error('操作失败，请稍后再试')
  }
}

/** 删除会话（确认后级联清理其消息与反馈） */
async function deleteConversationItem(id: number) {
  try {
    await ElMessageBox.confirm('删除后该会话及其消息记录将无法恢复，确定删除？', '删除会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return // 用户取消
  }
  try {
    await deleteConversation(id)
    aiConversations.value = aiConversations.value.filter((c) => c.id !== id)
    if (aiConversationId.value === id) {
      if (aiConversations.value.length > 0) {
        await loadConversation(aiConversations.value[0].id)
      } else {
        aiConversationId.value = null
        localStorage.removeItem('ai_conversation_id')
        aiMessages.value = []
      }
    }
  } catch {
    ElMessage.error('删除会话失败')
  }
}

/** 打开 AI 助手抽屉：刷新会话列表并恢复最近会话历史 */
/** 切换会话管理面板（展开时刷新列表；聊天记录保持原位，面板嵌入其上方） */
async function toggleConvPanel() {
  aiConvPanelVisible.value = !aiConvPanelVisible.value
  if (aiConvPanelVisible.value) {
    await refreshConversations()
  }
}

async function openAiDrawer() {
  aiVisible.value = true
  aiConvPanelVisible.value = false
  await refreshConversations()
  if (aiMessages.value.length > 0) return
  await loadConversation(aiConversationId.value)
}

/** 点击欢迎卡示例问题：直接作为用户输入发起对话 */
function askQuickQuestion(question: string) {
  if (aiLoading.value) return
  aiInput.value = question
  void sendAiMessage()
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
        refreshConversations()
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

<style>
/* AI 助手会话管理面板：紫色渐变氛围 + 柔光 + 动效（与「小江」品牌元素统一） */
.ai-conv-panel {
  background: linear-gradient(180deg, #fbfaff 0%, #ffffff 100%);
  border: 1px solid rgba(139, 92, 246, 0.10);
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.05);
  animation: ai-panel-in 0.22s ease-out both;
}
@keyframes ai-panel-in {
  from {
    opacity: 0;
    transform: translateY(-3px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.ai-conv-panel::-webkit-scrollbar {
  width: 4px;
}
.ai-conv-panel::-webkit-scrollbar-track {
  background: transparent;
}
.ai-conv-panel::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.18);
  border-radius: 2px;
}
.ai-conv-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 92, 246, 0.32);
}
.ai-conv-row {
  transition: background 0.2s ease;
}
.ai-conv-row:hover {
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.05), rgba(99, 102, 241, 0.02)) !important;
}
.ai-conv-group {
  display: flex;
  align-items: center;
}
.ai-conv-group::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  margin-right: 6px;
  opacity: 0.45;
  flex-shrink: 0;
}
.ai-panel-enter-active,
.ai-panel-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.ai-panel-enter-from,
.ai-panel-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.ai-quick-q {
  text-decoration: none;
  display: flex;
  align-items: center;
}
.ai-quick-q::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.75);
  margin-right: 8px;
  flex-shrink: 0;
}
.ai-quick-q:hover {
  background: rgba(64, 158, 255, 0.12);
  transform: translateX(2px);
}
</style>
