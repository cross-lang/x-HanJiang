<template>
  <el-container style="height: 100vh">
    <el-aside
      :width="isCollapsed ? '64px' : '200px'"
      style="
        background: #ffffff;
        border-right: 1px solid #e4e7ed;
        position: relative;
        transition: width 0.25s ease;
        overflow: hidden;
      "
    >
      <div class="app-title" :title="isCollapsed ? '点击展开菜单' : '点击收起菜单'" @click="toggleMenu">
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
      <el-header
        style="
          background: #fff;
          border-bottom: 1px solid #eee;
          display: flex;
          justify-content: flex-end;
          align-items: center;
          user-select: none;
          -webkit-user-select: none;
        "
      >
        <Search />
        <NotificationBell />
        <el-tooltip content="我是小江，您的 AI 助手" placement="bottom" effect="light" :show-after="200">
          <div class="ai-btn" @click="openAiDrawer">
            <div class="ai-entry">
              <el-icon :size="18"><MagicStick /></el-icon>
              <span>小江</span>
            </div>
          </div>
        </el-tooltip>
        <el-dropdown @command="handleCommand">
          <span style="cursor: pointer; display: flex; align-items: center; gap: 10px">
            <el-avatar :size="36" style="background: #79bbff">
              {{ (userStore.userInfo?.name || userStore.userInfo?.username || 'U').charAt(0) }}
            </el-avatar>
            <div style="line-height: 1.4">
              <div style="font-weight: 500; color: #333">
                {{ userStore.userInfo?.name || userStore.userInfo?.username || '用户' }}
              </div>
              <div style="font-size: 12px; color: #999">{{ userStore.userInfo?.email || '' }}</div>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile"
                ><el-icon style="margin-right: 8px"><User /></el-icon>个人中心</el-dropdown-item
              >
              <el-dropdown-item divided command="logout"
                ><el-icon style="margin-right: 8px"><SwitchButton /></el-icon>退出登录</el-dropdown-item
              >
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background: #f0f2f5; padding: 0; display: flex; flex-direction: column">
        <div
          v-if="!isHome"
          style="
            background: #fff;
            padding: 12px 20px;
            border-bottom: 1px solid #e4e7ed;
            display: flex;
            align-items: center;
            gap: 12px;
          "
        >
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
          <div class="app-footer-links">
            <a href="https://github.com/cross-lang/x-HanJiang" target="_blank" rel="noopener noreferrer" title="GitHub">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
                <path
                  d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
                />
              </svg>
            </a>
            <a href="https://gitee.com/cross-lang/x-HanJiang" target="_blank" rel="noopener noreferrer" title="Gitee">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
                <path
                  d="M2 6.5A4.5 4.5 0 0 1 6.5 2h11A4.5 4.5 0 0 1 22 6.5v11a4.5 4.5 0 0 1-4.5 4.5h-11A4.5 4.5 0 0 1 2 17.5v-11z"
                />
                <path fill="#fff" d="M5 9h14v1.3H5zm0 3.5h10v1.3H5z" />
              </svg>
            </a>
          </div>
          <span>Copyright © {{ currentYear }} 汉江管理系统 All Rights Reserved</span>
        </div>
      </el-main>
    </el-container>

    <!-- 小江 AI 助手抽屉 -->
    <el-drawer v-model="aiVisible" :size="`${aiDrawerWidth}px`" direction="rtl" class="ai-drawer-shell">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; padding: 0 4px">
          <div style="display: flex; align-items: center; gap: 10px">
            <div
              style="
                width: 30px;
                height: 30px;
                border-radius: 9px;
                background: linear-gradient(135deg, #8b5cf6, #6366f1);
                box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
              "
            >
              <el-icon size="16" color="#fff"><MagicStick /></el-icon>
            </div>
            <span style="font-size: 16px; font-weight: 600">小江</span>
          </div>
          <el-button text size="small" @click="toggleConvPanel">
            <el-icon><ChatDotRound /></el-icon>&nbsp;{{ aiConvPanelVisible ? '收起会话' : '会话管理' }}
          </el-button>
        </div>
      </template>
      <div style="display: flex; height: 100%">
        <div
          class="ai-drawer-split"
          :class="{ 'ai-drawer-split-active': draggingDrawer }"
          title="按住鼠标左右拖动，调整小江窗口宽度"
          @mousedown="startDrawerResize"
        ></div>
        <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; height: 100%">
          <!-- 会话管理面板：点击「会话管理」嵌入聊天区上方，聊天记录顺势下移 -->
          <transition name="ai-panel">
            <div v-if="aiConvPanelVisible" style="flex-shrink: 0; margin-bottom: 12px">
              <div
                class="ai-conv-panel"
                :style="`height: ${aiPanelHeight}px; overflow-y: auto; border-radius: 12px; padding: 12px 8px 8px`"
              >
                <!-- 标题行 -->
                <div
                  style="
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 4px 10px;
                    border-bottom: 1px solid rgba(144, 147, 153, 0.15);
                    margin-bottom: 6px;
                    cursor: pointer;
                    border-radius: 6px;
                    transition: background 0.15s;
                  "
                  title="点击收起会话面板"
                  @click="toggleConvPanel"
                  @mouseenter="($event.currentTarget as HTMLElement).style.background = 'rgba(144, 147, 153, 0.06)'"
                  @mouseleave="($event.currentTarget as HTMLElement).style.background = 'transparent'"
                >
                  <div style="display: flex; align-items: center; gap: 6px">
                    <span
                      style="
                        width: 3px;
                        height: 14px;
                        border-radius: 2px;
                        background: linear-gradient(180deg, #8b5cf6, #6366f1);
                        display: inline-block;
                      "
                    ></span>
                    <span style="font-size: 13px; color: #1f2329; font-weight: 600">会话列表</span>
                  </div>
                  <button
                    type="button"
                    style="
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
                    "
                    @mouseenter="($event.target as HTMLElement).style.filter = 'brightness(1.08)'"
                    @mouseleave="($event.target as HTMLElement).style.filter = 'none'"
                    @click.stop="createNewConversation"
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
                    style="padding: 6px 8px 3px; font-size: 12px; color: #6f6f7a; letter-spacing: 0.5px"
                  >
                    置顶
                  </div>
                  <div
                    v-else-if="!item.is_pinned && item.id === recentConvs[0]?.id"
                    class="ai-conv-group"
                    style="padding: 6px 8px 3px; font-size: 12px; color: #6f6f7a; letter-spacing: 0.5px"
                  >
                    最近
                  </div>
                  <!-- 会话行：左侧当前会话高亮条 + 名称时间 + 置顶/删除 -->
                  <div
                    class="ai-conv-row"
                    style="
                      display: flex;
                      align-items: center;
                      gap: 8px;
                      padding: 8px;
                      border-radius: 8px;
                      cursor: pointer;
                    "
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
                    <div style="flex: 1; min-width: 0">
                      <div
                        style="
                          font-size: 13px;
                          color: #333;
                          white-space: nowrap;
                          overflow: hidden;
                          text-overflow: ellipsis;
                        "
                      >
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
                        @mouseleave="
                          ($event.target as HTMLElement).style.color = item.is_pinned ? '#8b5cf6' : '#b8b8c2'
                        "
                        @click.stop="togglePin(item)"
                      >
                        <Paperclip />
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
              <div
                class="ai-panel-split"
                :class="{ 'ai-panel-split-active': draggingPanel }"
                title="按住鼠标上下拖动，调整会话面板高度"
                @mousedown="startPanelResize"
              ></div>
            </div>
          </transition>
          <!-- 聊天区 -->
          <div
            ref="chatScrollRef"
            style="
              flex: 1;
              overflow-y: auto;
              padding: 12px;
              background: #f7f8fd;
              border: 1px solid #e6e7f0;
              border-radius: 8px;
              margin-bottom: 12px;
            "
          >
            <div v-if="aiMessages.length === 0" style="text-align: center; color: #666; padding: 24px 12px">
              <div
                style="
                  width: 48px;
                  height: 48px;
                  margin: 0 auto 14px;
                  border-radius: 14px;
                  background: linear-gradient(135deg, #8b5cf6, #6366f1);
                  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
                  display: flex;
                  align-items: center;
                  justify-content: center;
                "
              >
                <el-icon size="22" color="#fff"><MagicStick /></el-icon>
              </div>
              <p style="margin: 0 0 6px; font-size: 16px; font-weight: 600; color: #1f2329; text-align: center">
                你好！我是小江，您的 AI 助手
              </p>
              <p style="font-size: 13px; color: #909399; margin-bottom: 14px; line-height: 1.6; text-align: left">
                不熟悉系统怎么操作？直接问我，我可以教你并帮你跳转到对应页面：
              </p>
              <div
                style="
                  text-align: left;
                  font-size: 14px;
                  line-height: 1.9;
                  color: #5a6cf0;
                  background: #eef1fc;
                  border-radius: 8px;
                  padding: 10px 14px;
                "
              >
                <div
                  class="ai-quick-q"
                  style="
                    cursor: pointer;
                    padding: 3px 6px;
                    margin: 0 -6px;
                    border-radius: 6px;
                    transition:
                      background 0.15s,
                      transform 0.15s;
                  "
                  @click="askQuickQuestion('怎么添加用户？')"
                >
                  <el-icon size="14" style="color: #5a6cf0; flex-shrink: 0"><Right /></el-icon>
                  怎么添加用户？
                </div>
                <div
                  class="ai-quick-q"
                  style="
                    cursor: pointer;
                    padding: 3px 6px;
                    margin: 0 -6px;
                    border-radius: 6px;
                    transition:
                      background 0.15s,
                      transform 0.15s;
                  "
                  @click="askQuickQuestion('帮我跳到权限管理')"
                >
                  <el-icon size="14" style="color: #5a6cf0; flex-shrink: 0"><Right /></el-icon>
                  帮我跳到权限管理
                </div>
                <div
                  class="ai-quick-q"
                  style="
                    cursor: pointer;
                    padding: 3px 6px;
                    margin: 0 -6px;
                    border-radius: 6px;
                    transition:
                      background 0.15s,
                      transform 0.15s;
                  "
                  @click="askQuickQuestion('用户列表在哪里？')"
                >
                  <el-icon size="14" style="color: #5a6cf0; flex-shrink: 0"><Right /></el-icon>
                  用户列表在哪里？
                </div>
                <div
                  class="ai-quick-q"
                  style="
                    cursor: pointer;
                    padding: 3px 6px;
                    margin: 0 -6px;
                    border-radius: 6px;
                    transition:
                      background 0.15s,
                      transform 0.15s;
                  "
                  @click="askQuickQuestion('怎么修改我的个人资料？')"
                >
                  <el-icon size="14" style="color: #5a6cf0; flex-shrink: 0"><Right /></el-icon>
                  怎么修改我的个人资料？
                </div>
              </div>
            </div>
            <div
              v-for="(msg, idx) in aiMessages"
              :key="idx"
              style="margin-bottom: 12px; display: flex; align-items: flex-end; gap: 8px"
              :style="msg.role === 'user' ? 'flex-direction: row-reverse' : 'flex-direction: row'"
            >
              <img
                v-if="msg.role === 'assistant'"
                :src="xiaoJiangLogo"
                alt="小江"
                style="
                  width: 26px;
                  height: 26px;
                  border-radius: 8px;
                  flex-shrink: 0;
                  object-fit: contain;
                  background: #eef1fc;
                  padding: 2px;
                  box-sizing: border-box;
                "
              />
              <div
                v-else
                style="
                  width: 26px;
                  height: 26px;
                  border-radius: 50%;
                  background: linear-gradient(135deg, #5b7cfa, #5a6cf0);
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  flex-shrink: 0;
                "
              >
                <el-icon size="13" color="#fff"><User /></el-icon>
              </div>
              <div style="display: flex; flex-direction: column; max-width: 80%; min-width: 0">
                <div
                  :style="
                    msg.role === 'user'
                      ? 'background: linear-gradient(135deg, #5b7cfa, #5a6cf0); color: #fff; font-size: 13px; padding: 8px 12px; border-radius: 8px; white-space: pre-wrap; word-break: break-word'
                      : 'background: #fff; color: #333; font-size: 13px; border: 1px solid #e4e7ed; padding: 8px 12px; border-radius: 8px; white-space: pre-wrap; word-break: break-word'
                  "
                >
                  <span v-if="msg.loading && !msg.content" class="ai-typing"
                    >正在思考<span class="ai-dot">…</span></span
                  >
                  <template v-else>{{ msg.content }}</template>
                </div>
                <div
                  v-if="msg.role === 'assistant' && msg.messageId != null && msg.content"
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
          </div>
          <!-- 输入区：底部留白，避免贴边下沉 -->
          <div style="display: flex; gap: 8px; padding: 0 0 18px">
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
  </el-container>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import Search from '@/components/Search.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import xiaoJiangLogo from '@/assets/xiaojiang-logo.png'
import { formatMonthDayTime } from '@/utils/format'
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
import type { MenuItem } from '@/types/auth'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const currentYear = new Date().getFullYear()

// 当前是否为首页（/dashboard 或根路径 /）
const isHome = computed(() => route.path === '/dashboard' || route.path === '/')

const aiVisible = ref(false)
// 抽屉整体宽度（左缘拖拽条可左右调整，扩大横向视野；380~760px 夹取）
const aiDrawerWidth = ref(420)
const draggingDrawer = ref(false)
const startX = ref(0)
const startW = ref(0)

/** 抽屉左缘拖拽条按下：记录起点，阻止默认（防文本选中），挂全局监听 */
function startDrawerResize(e: MouseEvent): void {
  e.preventDefault()
  draggingDrawer.value = true
  startX.value = e.clientX
  startW.value = aiDrawerWidth.value
  document.body.classList.add('ai-resizing')
  document.addEventListener('mousemove', onDrawerResize)
  document.addEventListener('mouseup', endDrawerResize)
}

/** 拖动中：抽屉在右侧，向左拖（clientX 减小）则宽度增大 */
function onDrawerResize(e: MouseEvent): void {
  if (!draggingDrawer.value) return
  const delta = startX.value - e.clientX
  aiDrawerWidth.value = Math.min(760, Math.max(380, startW.value + delta))
}

/** 松开：移除全局监听，恢复文本可选 */
function endDrawerResize(): void {
  draggingDrawer.value = false
  document.body.classList.remove('ai-resizing')
  document.removeEventListener('mousemove', onDrawerResize)
  document.removeEventListener('mouseup', endDrawerResize)
}
// 会话管理面板：展开时嵌入聊天区上方（不弹窗、不分栏）
const aiConvPanelVisible = ref(false)
// 会话面板高度（可拖拽分隔条调整，120~400px 夹取；聊天区 flex 自动伸缩）
const aiPanelHeight = ref(220)
const draggingPanel = ref(false)
const startY = ref(0)
const startH = ref(0)

/** 分隔条按下：记录起点，阻止默认（防文本选中），挂全局移动/松开监听 */
function startPanelResize(e: MouseEvent): void {
  e.preventDefault()
  draggingPanel.value = true
  startY.value = e.clientY
  startH.value = aiPanelHeight.value
  document.body.classList.add('ai-resizing')
  document.addEventListener('mousemove', onPanelResize)
  document.addEventListener('mouseup', endPanelResize)
}

/** 拖动中：按位移更新面板高度 */
function onPanelResize(e: MouseEvent): void {
  if (!draggingPanel.value) return
  const delta = e.clientY - startY.value
  aiPanelHeight.value = Math.min(400, Math.max(120, startH.value + delta))
}

/** 松开：移除全局监听，恢复文本可选 */
function endPanelResize(): void {
  draggingPanel.value = false
  document.body.classList.remove('ai-resizing')
  document.removeEventListener('mousemove', onPanelResize)
  document.removeEventListener('mouseup', endPanelResize)
}

onBeforeUnmount(() => {
  endPanelResize()
  endDrawerResize()
})
const aiInput = ref('')
const aiLoading = ref(false)
// 最近会话ID（续聊上下文；null 表示新会话，首轮由后端自动创建）
const aiConversationId = ref<number | null>(Number(localStorage.getItem('ai_conversation_id')) || null)
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
const pinnedConvs = computed(() => aiConversations.value.filter(c => c.is_pinned))
const recentConvs = computed(() => aiConversations.value.filter(c => !c.is_pinned))

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
    const res = await listConversations()
    aiConversations.value = res?.data ?? []
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
  return formatMonthDayTime(item.updated_at)
}

/** 加载指定会话的历史消息并设为当前会话 */
async function loadConversation(id: number | null) {
  if (id === null) {
    aiMessages.value = []
    return
  }
  try {
    const res = await getConversationMessages(id)
    const items: MessageItem[] = res?.data ?? []
    aiMessages.value = items.map(item => ({
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
    const res = await createConversation()
    const conv = res?.data
    if (conv?.id) {
      aiConversations.value = [conv, ...aiConversations.value.filter(c => c.id !== conv.id)]
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
    aiConversations.value = aiConversations.value.filter(c => c.id !== id)
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
      onToken: chunk => {
        assistantMsg.content += chunk
      },
      onNavigate: path => {
        // 跳转指令：执行路由跳转并关闭抽屉（剩余流式文本不再展示）
        router.push(path)
        aiVisible.value = false
      },
      onDenied: () => {
        // 越权拒绝：模型随后会流式说明，无需额外动作
      },
      onError: message => {
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
  } catch (err) {
    assistantMsg.loading = false
    assistantMsg.content = (err as Error)?.message || '网络异常，请稍后再试'
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
  const findTitle = (list: MenuItem[], path: string): string => {
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
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
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
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 12px 0 20px;
  color: #909399;
  font-size: 12px;
  user-select: none;
}
.app-footer-links {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 14px;
}
.app-footer-links a {
  color: #909399;
  display: inline-flex;
  align-items: center;
  transition: color 0.15s;
}
.app-footer-links a:hover {
  color: #409eff;
}
</style>

<style>
/* 全局禁止拖选文本（防黑框圈选），输入类控件除外 */
body {
  user-select: none;
  -webkit-user-select: none;
}
input,
textarea,
[contenteditable='true'] {
  user-select: text;
  -webkit-user-select: text;
}

/* 拖拽期间全局禁止文本选中（防黑框圈选） */
body.ai-resizing {
  user-select: none;
  -webkit-user-select: none;
}

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
}
.ai-quick-q:hover {
  background: rgba(64, 158, 255, 0.12);
  transform: translateX(2px);
}
</style>
