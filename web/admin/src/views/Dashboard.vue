<template>
  <div>
    <!-- 欢迎信息 -->
    <el-card>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <div style="font-size: 20px; font-weight: 500">
            欢迎回来，{{ userStore.userInfo?.name || userStore.userInfo?.username }}
          </div>
          <div style="color: #999; margin-top: 5px">今天是 {{ today }}</div>
        </div>
      </div>
    </el-card>

    <!-- 公告横幅（首页通栏） -->
    <div v-if="bannerAnnouncements.length" style="margin-top: 20px">
      <div
        v-for="item in bannerAnnouncements"
        :key="'b-' + item.id"
        class="announcement-banner"
        @click="openAnnouncement(item)"
      >
        <el-icon style="font-size: 20px; flex-shrink: 0"><Notification /></el-icon>
        <div style="flex: 1; min-width: 0">
          <div style="font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ item.title }}</div>
          <div style="font-size: 12px; margin-top: 4px; opacity: 0.9">
            有效期至 {{ fmtTime(item.end_at) }}
          </div>
        </div>
        <el-icon style="font-size: 18px"><ArrowRight /></el-icon>
      </div>
    </div>

    <!-- 公告板块（列表） -->
    <el-card v-if="boardAnnouncements.length" style="margin-top: 20px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>公告</span>
          <span style="font-size: 12px; color: #999">{{ boardAnnouncements.length }} 条进行中</span>
        </div>
      </template>
      <div
        v-for="item in boardAnnouncements"
        :key="'n-' + item.id"
        class="announcement-item"
        @click="openAnnouncement(item)"
      >
        <span class="announcement-dot" />
        <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ item.title }}</span>
        <span style="color: #999; font-size: 12px">{{ fmtTime(item.end_at) }}</span>
      </div>
    </el-card>

    <!-- 快捷入口 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6" v-for="item in quickLinks" :key="item.path">
        <el-card shadow="hover" style="cursor: pointer" @click="$router.push(item.path)">
          <div style="display: flex; align-items: center; gap: 16px">
            <div :style="{
              width: '48px', height: '48px', borderRadius: '8px',
              background: item.color, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: '24px',
            }">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div>
              <div style="font-weight: 500; font-size: 15px">{{ item.title }}</div>
              <div style="color: #999; font-size: 12px; margin-top: 4px">{{ item.desc }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 我的最近动态 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>我的最近登录</span>
              <el-button text type="primary" size="small" @click="$router.push('/audit/login?mine=true')">查看全部</el-button>
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
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="justify-content: space-between; align-items: center; display: flex">
              <span>我的最近操作</span>
              <el-button text type="primary" size="small" @click="$router.push('/audit?mine=true')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="myAudits" size="small" empty-text="暂无记录">
            <el-table-column prop="entity_type" label="实体" width="100" />
            <el-table-column prop="action" label="操作" width="80" />
            <el-table-column prop="ip_address" label="IP" width="120" />
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 公告详情对话框 -->
    <el-dialog v-model="announcementVisible" title="公告详情" width="680px">
      <template v-if="announcementDetail">
        <div style="font-size: 18px; font-weight: 600; margin-bottom: 12px">{{ announcementDetail.title }}</div>
        <div style="color: #999; font-size: 12px; margin-bottom: 12px">
          有效期：{{ fmtTime(announcementDetail.start_at) }} ~ {{ fmtTime(announcementDetail.end_at) }}
        </div>
        <div class="announcement-preview" v-html="renderAnnouncement(announcementDetail.content, announcementDetail.content_type)" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'
import { renderAnnouncement } from '@/utils/announcement'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const allQuickLinks = [
  { title: '用户管理', desc: '查看和管理系统用户', path: '/users', icon: 'User', color: '#409eff', perm: 'user:view' },
  { title: '角色管理', desc: '分配角色和权限', path: '/roles', icon: 'UserFilled', color: '#67c23a', perm: 'role:view' },
  { title: '开放应用', desc: '管理第三方接入应用', path: '/apps', icon: 'Grid', color: '#e6a23c', perm: 'openapi_app:view' },
  { title: '个人中心', desc: '修改个人信息和密码', path: '/profile', icon: 'Setting', color: '#909399', perm: '' },
]

const permissions = userStore.userInfo?.permissions || []
const quickLinks = allQuickLinks.filter(l => !l.perm || permissions.includes('*') || permissions.includes(l.perm))
const myLogins = ref<any[]>([])
const myAudits = ref<any[]>([])

const announcements = ref<any[]>([])
const announcementVisible = ref(false)
const announcementDetail = ref<any>(null)

const bannerAnnouncements = computed(() => announcements.value.filter(a => a.position === 'banner'))
const boardAnnouncements = computed(() => announcements.value.filter(a => a.position === 'board'))

function fmtTime(v: string | null | undefined): string {
  if (!v) return ''
  return v.replace('T', ' ').slice(0, 16)
}

async function fetchAnnouncements() {
  try {
    const res = await request.get('/announcements/available')
    announcements.value = res.data.items || []
  } catch (e) {
    // 公告接口不可用时静默
  }
}

function openAnnouncement(item: any) {
  announcementDetail.value = item
  announcementVisible.value = true
}

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const res = await request.get('/dashboard/my-activity')
    myLogins.value = res.data.recent_logins
    myAudits.value = res.data.recent_audits
  } catch (e) {
    // 静默处理
  }
  await fetchAnnouncements()
})
</script>

<style scoped>
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
