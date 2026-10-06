<template>
  <div>
    <!-- 欢迎信息 -->
    <el-card>
      <div class="hj-flex-between">
        <div>
          <div class="welcome-title">欢迎回来，{{ userStore.userInfo?.name || userStore.userInfo?.username }}</div>
          <div class="welcome-sub">今天是 {{ today }}</div>
        </div>
      </div>
    </el-card>

    <!-- 公告横幅（首页通栏） -->
    <div v-if="bannerAnnouncements.length" class="hj-mt-20">
      <div
        v-for="item in bannerAnnouncements"
        :key="'b-' + item.id"
        class="announcement-banner"
        @click="openAnnouncement(item)"
      >
        <el-icon class="banner-icon"><Notification /></el-icon>
        <div class="hj-flex-1">
          <div class="banner-title">{{ item.title }}</div>
          <div class="banner-sub">有效期至 {{ formatDateTimeShort(item.end_at) }}</div>
        </div>
        <el-icon class="banner-arrow"><ArrowRight /></el-icon>
      </div>
    </div>

    <!-- 公告板块（列表） -->
    <el-card v-if="boardAnnouncements.length" class="hj-mt-20">
      <template #header>
        <div class="hj-flex-between">
          <span>公告</span>
          <span class="hj-text-12 hj-text-gray">{{ boardAnnouncements.length }} 条进行中</span>
        </div>
      </template>
      <div
        v-for="item in boardAnnouncements"
        :key="'n-' + item.id"
        class="announcement-item"
        @click="openAnnouncement(item)"
      >
        <span class="announcement-dot" />
        <span class="hj-ellipsis hj-flex-1">{{ item.title }}</span>
        <span class="hj-text-gray hj-text-12">{{ formatDateTimeShort(item.end_at) }}</span>
      </div>
    </el-card>

    <!-- 快捷入口 -->
    <el-row :gutter="20" class="hj-mt-20">
      <el-col :span="6" v-for="item in quickLinks" :key="item.path">
        <el-card shadow="hover" class="quick-card" @click="$router.push(item.path)">
          <div class="quick-inner">
            <div class="quick-icon" :style="{ background: item.color }">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div>
              <div class="quick-title">{{ item.title }}</div>
              <div class="quick-desc">{{ item.desc }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 我的最近动态（仅 home:view 权限可见） -->
    <el-row v-if="canViewHome" :gutter="20" class="hj-mt-20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="hj-flex-between">
              <span>我的最近登录</span>
              <el-button text type="primary" size="small" @click="$router.push('/logs/login?mine=true')"
                >查看全部</el-button
              >
            </div>
          </template>
          <el-table :data="myLogins" size="small" empty-text="暂无记录">
            <el-table-column prop="ip_address" label="IP" width="120" />
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatMonthDayTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="hj-flex-between">
              <span>我的最近操作</span>
              <el-button text type="primary" size="small" @click="$router.push('/logs/audit?mine=true')"
                >查看全部</el-button
              >
            </div>
          </template>
          <el-table :data="myAudits" size="small" empty-text="暂无记录">
            <el-table-column label="实体" width="140">
              <template #default="{ row }">{{ formatAuditEntity(row.entity_type) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">{{ formatAuditAction(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="ip_address" label="IP" width="120" />
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatMonthDayTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 公告详情对话框 -->
    <el-dialog v-model="announcementVisible" title="公告详情" width="680px">
      <template v-if="announcementDetail">
        <div class="dialog-title">{{ announcementDetail.title }}</div>
        <div class="dialog-meta">
          有效期：{{ formatDateTimeShort(announcementDetail.start_at) }} ~
          {{ formatDateTimeShort(announcementDetail.end_at) }}
        </div>
        <div
          class="announcement-preview"
          v-html="renderAnnouncement(announcementDetail.content, announcementDetail.content_type)"
        />
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { renderAnnouncement } from '@/utils/announcement'
import { formatDateTimeShort, formatMonthDayTime } from '@/utils/format'
import { formatAuditEntity, formatAuditAction } from '@/utils/audit-labels'
import { getMyActivity } from '@/api/home'
import { listAvailableAnnouncements } from '@/api/announcement'
import type { AnnouncementItem } from '@/types/announcement'
import type { MyActivity } from '@/types/home'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long',
})

const allQuickLinks = [
  { title: '用户管理', desc: '查看和管理系统用户', path: '/users', icon: 'User', color: '#409eff', perm: 'user:view' },
  {
    title: '角色管理',
    desc: '分配角色和权限',
    path: '/roles',
    icon: 'UserFilled',
    color: '#67c23a',
    perm: 'role:view',
  },
  {
    title: '开放应用',
    desc: '管理第三方接入应用',
    path: '/apps',
    icon: 'Grid',
    color: '#e6a23c',
    perm: 'openapi_app:view',
  },
  { title: '个人中心', desc: '修改个人信息和密码', path: '/profile', icon: 'Setting', color: '#909399', perm: '' },
]

const permissions = userStore.userInfo?.permissions || []
// 首页页面权限：无 home:view 时不请求"我的最近活动"，避免 403
const canViewHome = userStore.hasPerm('home:view')
const quickLinks = allQuickLinks.filter(l => !l.perm || permissions.includes('*') || permissions.includes(l.perm))
const myLogins = ref<MyActivity['recent_logins']>([])
const myAudits = ref<MyActivity['recent_audits']>([])

const announcements = ref<AnnouncementItem[]>([])
const announcementVisible = ref(false)
const announcementDetail = ref<AnnouncementItem | null>(null)

const bannerAnnouncements = computed(() => announcements.value.filter(a => a.position === 'banner'))
const boardAnnouncements = computed(() => announcements.value.filter(a => a.position === 'board'))

async function fetchAnnouncements() {
  try {
    const res = await listAvailableAnnouncements()
    announcements.value = res.data.items || []
  } catch {
    // 公告接口不可用时静默
  }
}

function openAnnouncement(item: AnnouncementItem) {
  announcementDetail.value = item
  announcementVisible.value = true
}

onMounted(async () => {
  if (canViewHome) {
    try {
      const res = await getMyActivity()
      myLogins.value = res.data.recent_logins
      myAudits.value = res.data.recent_audits
    } catch {
      // 静默处理
    }
  }
  await fetchAnnouncements()
})
</script>

<style scoped>
.welcome-title {
  font-size: 20px;
  font-weight: 500;
}
.welcome-sub {
  color: #999;
  margin-top: 5px;
}
.quick-card {
  cursor: pointer;
}
.quick-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}
.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  flex-shrink: 0;
}
.quick-title {
  font-weight: 500;
  font-size: 15px;
}
.quick-desc {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}
.banner-icon {
  font-size: 20px;
  flex-shrink: 0;
}
.banner-title {
  font-size: 15px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.banner-sub {
  font-size: 12px;
  margin-top: 4px;
  opacity: 0.9;
}
.banner-arrow {
  font-size: 18px;
}
.dialog-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 12px;
}
.dialog-meta {
  color: #999;
  font-size: 12px;
  margin-bottom: 12px;
}
.announcement-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(90deg, #409eff, #66b1ff);
  color: #fff;
  border-radius: 8px;
  padding: 14px 20px;
  margin-bottom: 12px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
}
.announcement-banner:hover {
  opacity: 0.92;
}
.announcement-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.announcement-item:hover {
  background: var(--el-fill-color-light);
}
.announcement-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
}
.announcement-preview {
  line-height: 1.7;
  max-height: 400px;
  overflow: auto;
}
</style>
