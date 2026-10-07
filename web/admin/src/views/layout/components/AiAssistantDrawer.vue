<template>
  <el-drawer v-model="visible" :size="`${aiDrawerWidth}px`" direction="rtl" class="ai-drawer-shell">
    <template #header>
      <div class="ai-drawer-header">
        <div class="ai-drawer-title">
          <div class="ai-avatar-badge">
            <el-icon size="16" color="#fff"><MagicStick /></el-icon>
          </div>
          <span class="ai-drawer-name">小江</span>
        </div>
        <el-button text size="small" class="ai-conv-toggle" @click="toggleConvPanel">
          <el-icon><ChatDotRound /></el-icon>&nbsp;{{ aiConvPanelVisible ? '收起会话' : '会话管理' }}
        </el-button>
      </div>
    </template>
    <div class="ai-drawer-body">
      <div
        class="ai-drawer-split"
        :class="{ 'ai-drawer-split-active': draggingDrawer }"
        title="按住鼠标左右拖动，调整小江窗口宽度"
        @mousedown="startDrawerResize"
      ></div>
      <div class="ai-drawer-content">
        <!-- 会话管理面板：点击「会话管理」嵌入聊天区上方，聊天记录顺势下移 -->
        <transition name="ai-panel">
          <div v-if="aiConvPanelVisible" class="ai-conv-wrap">
            <div
              class="ai-conv-panel"
              :style="`height: ${aiPanelHeight}px; overflow-y: auto; border-radius: 12px; padding: 12px 8px 8px`"
            >
              <!-- 标题行 -->
              <div
                class="ai-conv-head"
                title="点击收起会话面板"
                @click="toggleConvPanel"
                @mouseenter="($event.currentTarget as HTMLElement).style.background = 'rgba(144, 147, 153, 0.06)'"
                @mouseleave="($event.currentTarget as HTMLElement).style.background = 'transparent'"
              >
                <div class="ai-conv-head-left">
                  <span class="ai-conv-bar"></span>
                  <span class="ai-conv-head-text">会话列表</span>
                </div>
                <button
                  type="button"
                  class="ai-new-conv"
                  @mouseenter="($event.target as HTMLElement).style.filter = 'brightness(1.08)'"
                  @mouseleave="($event.target as HTMLElement).style.filter = 'none'"
                  @click.stop="createNewConversation"
                >
                  <el-icon size="12"><Plus /></el-icon>&nbsp;新建会话
                </button>
              </div>
              <!-- 列表 -->
              <div v-if="aiConversations.length === 0" class="ai-conv-empty">
                <el-icon size="28" color="#d5d3e8"><ChatDotRound /></el-icon>
                <p class="ai-conv-empty-text">还没有会话，点击「新建会话」开始对话</p>
              </div>
              <div v-for="item in aiConversations" :key="item.id" class="ai-conv-item">
                <!-- 分组标签：置顶 / 最近 -->
                <div v-if="item.is_pinned && item.id === pinnedConvs[0]?.id" class="ai-conv-group ai-conv-label">
                  置顶
                </div>
                <div v-else-if="!item.is_pinned && item.id === recentConvs[0]?.id" class="ai-conv-group ai-conv-label">
                  最近
                </div>
                <!-- 会话行：左侧当前会话高亮条 + 名称时间 + 置顶/删除 -->
                <div
                  class="ai-conv-row"
                  :style="item.id === aiConversationId ? 'background: rgba(144, 147, 153, 0.10)' : ''"
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
                  <div class="ai-conv-main">
                    <div class="ai-conv-name">{{ convTitle(item) }}</div>
                    <div class="ai-conv-time">{{ convTime(item) }}</div>
                  </div>
                  <div class="ai-conv-actions">
                    <el-icon
                      :color="item.is_pinned ? '#8b5cf6' : '#b8b8c2'"
                      :title="item.is_pinned ? '取消置顶' : '置顶'"
                      class="ai-conv-act"
                      @mouseenter="($event.target as HTMLElement).style.color = '#8b5cf6'"
                      @mouseleave="($event.target as HTMLElement).style.color = item.is_pinned ? '#8b5cf6' : '#b8b8c2'"
                      @click.stop="togglePin(item)"
                    >
                      <Paperclip />
                    </el-icon>
                    <el-icon
                      title="删除"
                      class="ai-conv-act ai-conv-del"
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
            <div
              class="ai-panel-split"
              :class="{ 'ai-panel-split-active': draggingPanel }"
              title="按住鼠标上下拖动，调整会话面板高度"
              @mousedown="startPanelResize"
            ></div>
          </div>
        </transition>
        <!-- 聊天区 -->
        <div ref="chatScrollRef" class="ai-chat-area">
          <div v-if="aiMessages.length === 0" class="ai-welcome">
            <div class="ai-welcome-logo">
              <el-icon size="22" color="#fff"><MagicStick /></el-icon>
            </div>
            <p class="ai-welcome-title">你好！我是小江，您的 AI 助手</p>
            <p class="ai-welcome-desc">不熟悉系统怎么操作？直接问我，我可以教你并帮你跳转到对应页面：</p>
            <div class="ai-welcome-qs">
              <div class="ai-quick-q" @click="askQuickQuestion('怎么添加用户？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么添加用户？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('帮我跳到权限管理')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                帮我跳到权限管理
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('用户列表在哪里？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                用户列表在哪里？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('怎么修改我的个人资料？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么修改我的个人资料？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('怎么管理开放平台应用？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么管理开放平台应用？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('怎么处理应用审批？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么处理应用审批？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('怎么查看审计日志？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么查看审计日志？
              </div>
              <div class="ai-quick-q" @click="askQuickQuestion('怎么查看登录日志？')">
                <el-icon size="14" class="ai-q-arrow"><Right /></el-icon>
                怎么查看登录日志？
              </div>
            </div>
          </div>
          <div
            v-for="(msg, idx) in aiMessages"
            :key="idx"
            class="ai-msg"
            :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
          >
            <img v-if="msg.role === 'assistant'" :src="xiaoJiangLogo" alt="小江" class="ai-msg-avatar" />
            <div v-else class="ai-msg-avatar ai-msg-avatar-user">
              <el-icon size="13" color="#fff"><User /></el-icon>
            </div>
            <div class="ai-msg-body">
              <div :class="msg.role === 'user' ? 'ai-bubble ai-bubble-user' : 'ai-bubble ai-bubble-assistant'">
                <span v-if="msg.loading && !msg.content" class="ai-typing">正在思考<span class="ai-dot">…</span></span>
                <template v-else>{{ msg.content }}</template>
              </div>
              <div v-if="msg.role === 'assistant' && msg.messageId != null && msg.content" class="ai-feedback">
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
        </div>
        <!-- 输入区：底部留白，避免贴边下沉 -->
        <div class="ai-input-area">
          <el-input
            v-model="aiInput"
            placeholder="输入你的问题..."
            :disabled="aiLoading"
            @keyup.enter="sendAiMessage"
          />
          <el-button type="primary" :loading="aiLoading" :disabled="aiLoading" @click="sendAiMessage">发送</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import xiaoJiangLogo from '@/assets/xiaojiang-logo.png'
import { useDragResize } from '@/composables/useDragResize'
import { useChatSse } from '@/composables/useChatSse'
import { useConversations } from '@/composables/useConversations'

const visible = defineModel<boolean>('visible', { required: true })
const router = useRouter()

// 抽屉整体宽度（左缘拖拽条可左右调整，扩大横向视野；380~760px 夹取）
const {
  size: aiDrawerWidth,
  dragging: draggingDrawer,
  startResize: startDrawerResize,
} = useDragResize({
  axis: 'x',
  min: 380,
  max: 760,
  initial: 420,
  invert: true,
})

// 会话面板高度（可拖拽分隔条调整，120~400px 夹取；聊天区 flex 自动伸缩）
const {
  size: aiPanelHeight,
  dragging: draggingPanel,
  startResize: startPanelResize,
} = useDragResize({
  axis: 'y',
  min: 120,
  max: 400,
  initial: 220,
})

// 聊天核心：SSE 流式对话、历史加载、自动滚底、反馈
const chat = useChatSse({
  onNavigate: path => {
    // 跳转指令：执行路由跳转，保持抽屉打开以便继续对话
    router.push(path)
  },
  onConversationsChange: () => void conversations.refreshConversations(),
})

// 会话列表：新建/置顶/删除/切换，经 conversationId 与聊天核心弱耦合
const conversations = useConversations(chat.aiConversationId, id => chat.loadConversation(id))

const {
  aiInput,
  aiLoading,
  aiConversationId,
  aiMessages,
  chatScrollRef,
  loadConversation,
  askQuickQuestion,
  sendAiMessage,
  submitAiFeedback,
} = chat
const {
  aiConversations,
  aiConvHoverId,
  pinnedConvs,
  recentConvs,
  refreshConversations,
  convTitle,
  convTime,
  createNewConversation,
  togglePin,
  deleteConversationItem,
} = conversations

// 会话管理面板：展开时嵌入聊天区上方（不弹窗、不分栏）
const aiConvPanelVisible = ref(false)

/** 切换会话管理面板（展开时刷新列表；聊天记录保持原位，面板嵌入其上方） */
async function toggleConvPanel() {
  aiConvPanelVisible.value = !aiConvPanelVisible.value
  if (aiConvPanelVisible.value) {
    await refreshConversations()
  }
}

/** 切换会话 */
async function switchConversation(id: number) {
  aiConvPanelVisible.value = false
  await loadConversation(id)
}

/** 打开抽屉：先拉会话列表，再校验残留的 aiConversationId 是否属于本用户 */
watch(visible, async v => {
  if (!v) return
  aiConvPanelVisible.value = false
  await refreshConversations()
  // 跨账号登录后 localStorage 可能残留旧会话 ID：不在当前用户列表里则丢弃，避免 404
  if (aiConversationId.value !== null && !aiConversations.value.some(c => c.id === aiConversationId.value)) {
    aiConversationId.value = null
    localStorage.removeItem('ai_conversation_id')
  }
  if (aiMessages.value.length === 0) {
    void loadConversation(aiConversationId.value)
  }
})
</script>

<style scoped>
/* ===== 抽屉头部 ===== */
.ai-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 4px;
}
.ai-drawer-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ai-avatar-badge {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-drawer-name {
  font-size: 16px;
  font-weight: 600;
}
/* 会话管理按钮：比 small 默认字号略放大 */
.ai-conv-toggle {
  font-size: 14px;
}

/* ===== 抽屉主体 ===== */
.ai-drawer-body {
  display: flex;
  height: 100%;
}
.ai-drawer-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ===== 会话管理面板 ===== */
.ai-conv-wrap {
  flex-shrink: 0;
  margin-bottom: 12px;
}
.ai-conv-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 10px;
  border-bottom: 1px solid rgba(144, 147, 153, 0.15);
  margin-bottom: 6px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}
.ai-conv-head-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ai-conv-bar {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: linear-gradient(180deg, #8b5cf6, #6366f1);
  display: inline-block;
}
.ai-conv-head-text {
  font-size: 13px;
  color: #1f2329;
  font-weight: 600;
}
.ai-new-conv {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 5px 10px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 1px 4px rgba(99, 102, 241, 0.3);
  transition: filter 0.15s;
  outline: none;
}
.ai-conv-empty {
  text-align: center;
  padding: 20px 8px;
}
.ai-conv-empty-text {
  margin: 8px 0 0;
  font-size: 12px;
  color: #8f8f99;
}
.ai-conv-item {
  margin-bottom: 2px;
}
.ai-conv-label {
  padding: 6px 8px 10px;
  font-size: 12px;
  color: #6f6f7a;
  letter-spacing: 0.5px;
}
.ai-conv-main {
  flex: 1;
  min-width: 0;
}
.ai-conv-name {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ai-conv-time {
  font-size: 11px;
  color: #a3a3ad;
  margin-top: 2px;
}
.ai-conv-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.ai-conv-act {
  cursor: pointer;
  padding: 3px;
  border-radius: 4px;
}

/* ===== 聊天区 ===== */
.ai-chat-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #f7f8fd;
  border: 1px solid #e6e7f0;
  border-radius: 8px;
  margin-bottom: 12px;
}
.ai-welcome {
  text-align: center;
  color: #666;
  padding: 24px 12px;
}
.ai-welcome-logo {
  width: 48px;
  height: 48px;
  margin: 0 auto 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-welcome-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2329;
  text-align: center;
}
.ai-welcome-desc {
  font-size: 13px;
  color: #909399;
  margin-bottom: 14px;
  line-height: 1.6;
  text-align: left;
}
.ai-welcome-qs {
  text-align: left;
  font-size: 14px;
  line-height: 1.9;
  color: #5a6cf0;
  background: #eef1fc;
  border-radius: 8px;
  padding: 10px 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 10px;
}
.ai-q-arrow {
  color: #5a6cf0;
  flex-shrink: 0;
}
.ai-msg {
  margin-bottom: 12px;
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.ai-msg.is-user {
  flex-direction: row-reverse;
}
.ai-msg.is-assistant {
  flex-direction: row;
}
.ai-msg-avatar {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  flex-shrink: 0;
  object-fit: contain;
  background: #eef1fc;
  padding: 2px;
  box-sizing: border-box;
}
.ai-msg-avatar-user {
  border-radius: 50%;
  background: linear-gradient(135deg, #5b7cfa, #5a6cf0);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ai-msg-body {
  display: flex;
  flex-direction: column;
  max-width: 80%;
  min-width: 0;
}
.ai-bubble {
  font-size: 13px;
  padding: 8px 12px;
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}
.ai-bubble-user {
  background: linear-gradient(135deg, #5b7cfa, #5a6cf0);
  color: #fff;
}
.ai-bubble-assistant {
  background: #fff;
  color: #333;
  border: 1px solid #e4e7ed;
}
.ai-feedback {
  display: flex;
  gap: 2px;
  margin-top: 2px;
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

/* ===== 输入区 ===== */
.ai-input-area {
  display: flex;
  gap: 8px;
  padding: 0 0 18px;
}
</style>

<style>
/* AI 助手抽屉：body 去内边距，左缘拖拽条贴边 */
.ai-drawer-shell .el-drawer__body {
  padding: 0;
}
.ai-drawer-split {
  width: 8px;
  height: 100%;
  cursor: col-resize;
  flex-shrink: 0;
  position: relative;
  transition: background 0.15s;
}
.ai-drawer-split::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 3px;
  height: 48px;
  border-radius: 2px;
  background: transparent;
  transition: background 0.15s;
}
.ai-drawer-split:hover {
  background: rgba(144, 147, 153, 0.1);
}
.ai-drawer-split:hover::after,
.ai-drawer-split-active::after {
  background: rgba(64, 158, 255, 0.55);
}
.ai-drawer-split-active {
  background: rgba(64, 158, 255, 0.12);
}

/* AI 助手会话管理面板：紫色渐变氛围 + 柔光 + 动效（与「小江」品牌元素统一） */
.ai-conv-panel {
  background: #f6f7f9;
  border: 1px solid rgba(144, 147, 153, 0.18);
  border-bottom: 2px solid rgba(144, 147, 153, 0.28);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
  animation: ai-panel-in 0.22s ease-out both;
}
.ai-panel-split {
  height: 12px;
  margin-top: 4px;
  cursor: row-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  position: relative;
  transition: background 0.15s;
}
.ai-panel-split::after {
  content: '';
  width: 48px;
  height: 3px;
  border-radius: 2px;
  background: transparent;
  transition: background 0.15s;
}
.ai-panel-split:hover {
  background: rgba(144, 147, 153, 0.1);
}
.ai-panel-split:hover::after,
.ai-panel-split-active::after {
  background: rgba(64, 158, 255, 0.55);
}
.ai-panel-split-active {
  background: rgba(64, 158, 255, 0.12);
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
  background: rgba(144, 147, 153, 0.25);
  border-radius: 2px;
}
.ai-conv-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(144, 147, 153, 0.45);
}
.ai-conv-row {
  display: flex;
  align-items: center;
  gap: 6px;
  transition: background 0.2s ease;
}
.ai-conv-row:hover {
  background: rgba(144, 147, 153, 0.06) !important;
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
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
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
  gap: 6px;
  cursor: pointer;
  padding: 3px 6px;
  margin: 0 -6px;
  border-radius: 6px;
  transition:
    background 0.15s,
    transform 0.15s;
}
.ai-quick-q:hover {
  background: rgba(64, 158, 255, 0.12);
  transform: translateX(2px);
}
</style>
