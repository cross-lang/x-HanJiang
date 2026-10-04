<template>
  <div class="home-page">
    <!-- 欢迎横幅 -->
    <div class="hero-card">
      <div class="hero-left">
        <el-avatar :size="72" class="hero-avatar">{{ initial }}</el-avatar>
        <div class="hero-info">
          <div class="hero-name">{{ developerStore.profile?.name || developerStore.profile?.username }}</div>
          <div class="hero-sub">@{{ developerStore.profile?.username }}</div>
          <div class="hero-tags">
            <el-tag v-if="developerStore.profile?.certification_type === 'enterprise'" type="warning" size="small">
              企业开发者
            </el-tag>
            <el-tag v-else-if="developerStore.profile?.certification_type === 'personal'" type="success" size="small">
              个人开发者
            </el-tag>
            <el-tag v-else type="info" size="small">未认证</el-tag>
          </div>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <div class="stat-num">{{ appCount }}</div>
          <div class="stat-label">我的应用</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ scopeCount }}</div>
          <div class="stat-label">已获权限</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ endpointCount }}</div>
          <div class="stat-label">可调接口</div>
        </div>
      </div>
    </div>

    <!-- 快速入口 -->
    <el-row :gutter="20" class="hj-mt-20">
      <el-col :span="8" v-for="entry in quickEntries" :key="entry.path">
        <el-card shadow="never" class="entry-card" @click="router.push(entry.path)">
          <el-icon :size="28" class="entry-icon" :color="entry.color"><component :is="entry.icon" /></el-icon>
          <div class="entry-title">{{ entry.title }}</div>
          <div class="entry-desc">{{ entry.desc }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 接入指引 -->
    <el-card shadow="never" class="hj-mt-20 guide-card">
      <h3 class="guide-title">三步接入汉江开放能力</h3>
      <div class="guide-steps">
        <div v-for="(step, idx) in guideSteps" :key="step.title" class="guide-step">
          <div class="step-index">{{ idx + 1 }}</div>
          <div class="step-body">
            <div class="step-title">{{ step.title }}</div>
            <div class="step-desc">{{ step.desc }}</div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 能力模块 -->
    <el-card shadow="never" class="hj-mt-20 guide-card">
      <h3 class="guide-title">开放能力模块</h3>
      <div class="module-grid">
        <div v-for="m in modules" :key="m.code" class="module-card">
          <el-icon :size="22" class="module-icon" color="#409eff"><component :is="m.icon" /></el-icon>
          <div class="module-name">{{ m.name }}</div>
          <div class="module-scopes">
            <el-tag v-for="s in m.scopes" :key="s" size="small" class="hj-mr-4">{{ s }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { Document, FirstAidKit, Folder, Grid, Plus, User, UserFilled } from '@element-plus/icons-vue'
import { capabilityModules, totalCapabilityApis } from '@/data/capability'
import { useDeveloperStore } from '@/stores/developer'
import { listMyApps } from '@/api/apps'
import { useScopeCatalog } from '@/composables/useScopeCatalog'

const router = useRouter()
const developerStore = useDeveloperStore()
const { fetchScopes } = useScopeCatalog()

const appCount = ref(0)
const scopeCount = ref(0)

const initial = computed(() => (developerStore.profile?.name || 'D').charAt(0))

// 可调接口数：与开放能力目录条目数一致（见 src/data/capability.ts）
const endpointCount = ref(totalCapabilityApis)

const quickEntries = [
  { title: '创建应用', desc: '注册你的第一个开放平台应用', path: '/apps', icon: Plus, color: '#409eff' },
  { title: '开放能力', desc: '按模块查看开放接口文档', path: '/capability/user', icon: Document, color: '#67c23a' },
  { title: '个人中心', desc: '完善资料与开发者认证', path: '/profile', icon: User, color: '#e6a23c' },
]

const guideSteps = [
  { title: '注册开发者账号', desc: '在开放平台注册并完善开发者资料' },
  { title: '创建应用并申请权限', desc: '创建应用，按需申请 user:read / user:write 等 scope' },
  { title: '获取 App ID / App Key 对接', desc: '按鉴权方式（明文 / HMAC 签名）调用开放接口' },
]

// 开放能力模块卡片：与开放能力目录（capability.ts）联动，后端新增模块/接口时首页自动同步
const MODULE_ICONS: Record<string, Component> = {
  health: FirstAidKit,
  app: Grid,
  user: User,
  role: UserFilled,
  file: Folder,
}

const modules = computed(() =>
  capabilityModules.map(m => ({
    code: m.key,
    name: m.name,
    icon: MODULE_ICONS[m.key] || Grid,
    scopes: [...new Set(m.apis.map(a => a.scope).filter(s => s && s !== '仅需有效应用凭证'))],
  })),
)

onMounted(async () => {
  void fetchScopes()
  try {
    const res = await listMyApps({ page: 1, page_size: 100 })
    appCount.value = res.data.total
    const scopes = new Set<string>()
    for (const app of res.data.items) {
      for (const s of app.scopes) scopes.add(s)
    }
    scopeCount.value = scopes.size
  } catch {
    // 应用接口待后端实现：统计保持 0，页面其余内容正常展示
  }
})
</script>

<style scoped>
.home-page {
  max-width: 1080px;
  margin: 0 auto;
}

/* ===== 欢迎横幅 ===== */
.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  padding: 28px 32px;
  border-radius: 16px;
  background:
    radial-gradient(90% 140% at 100% 0%, rgba(64, 158, 255, 0.08) 0%, transparent 55%),
    var(--hj-bg-card);
  border: 1px solid var(--hj-border-lighter);
  box-shadow: var(--hj-shadow-card);
}
.hero-left {
  display: flex;
  align-items: center;
  gap: 20px;
}
.hero-avatar {
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  color: #fff;
  font-size: 28px;
  font-weight: 600;
  border: none;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
.hero-name {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.hero-sub {
  margin-top: 4px;
  font-size: 14px;
  color: var(--hj-text-secondary);
}
.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.hero-stats {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 26px;
  border-radius: 12px;
  background: var(--hj-bg-page);
  border: 1px solid var(--hj-border-lighter);
}
.stat-item {
  text-align: center;
  min-width: 64px;
}
.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--hj-text-title);
  font-family: var(--hj-font-mono);
}
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--hj-text-secondary);
}
.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--hj-border);
}

/* ===== 快速入口 ===== */
.entry-card {
  border-radius: 14px;
  border: 1px solid var(--hj-border-lighter);
  cursor: pointer;
  transition:
    box-shadow 0.2s ease,
    transform 0.2s ease,
    border-color 0.2s ease;
  position: relative;
  overflow: hidden;
}
.entry-card:hover {
  box-shadow: var(--hj-shadow-card-hover);
  transform: translateY(-3px);
  border-color: var(--hj-primary-border);
}
.entry-icon {
  margin-bottom: 12px;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--hj-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.entry-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.entry-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--hj-text-secondary);
}

/* ===== 指引与能力 ===== */
.guide-card {
  border-radius: 14px;
  border: 1px solid var(--hj-border-lighter);
}
.guide-title {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.guide-steps {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}
.guide-step {
  display: flex;
  gap: 12px;
  flex: 1;
  min-width: 240px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--hj-bg-page);
  border: 1px solid var(--hj-border-lighter);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.guide-step:hover {
  border-color: var(--hj-primary-border);
  box-shadow: var(--hj-shadow-card);
}
.step-index {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  color: #fff;
  font-weight: 600;
  font-size: 14px;
}
.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.step-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--hj-text-secondary);
}
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.module-card {
  border: 1px solid var(--hj-border-light);
  border-radius: 12px;
  padding: 18px 20px;
  background: var(--hj-bg-page);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}
.module-card:hover {
  border-color: var(--hj-primary-border);
  box-shadow: var(--hj-shadow-card);
  transform: translateY(-2px);
}
.module-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--hj-primary-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}
.module-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--hj-text-title);
  margin: 10px 0;
}
.module-scopes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
