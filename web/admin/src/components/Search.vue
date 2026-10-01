<template>
  <div ref="wrapRef" class="search">
    <div class="search-input-wrap">
      <el-icon class="search-icon"><Search /></el-icon>
      <input
        ref="inputRef"
        v-model="keyword"
        class="search-input"
        type="text"
        placeholder="全局搜索用户、角色、应用、文件、通知、公告…"
        @input="onInput"
        @focus="panelVisible = !!keyword.trim()"
        @keydown.enter.prevent="jumpFirst"
        @keydown.esc="closePanel"
      />
      <span v-if="!keyword" class="kbd">/</span>
    </div>

    <div v-if="panelVisible" class="search-panel" v-loading="loading">
      <template v-if="hasResults">
        <div v-for="cat in visibleCategories" :key="cat.key" class="search-group">
          <div class="group-title">{{ cat.label }}</div>
          <div
            v-for="item in results[cat.key]"
            :key="item.id"
            class="group-item"
            @mousedown.prevent="goTo(cat, item)"
          >
            <div class="item-main">{{ itemTitle(cat, item) }}</div>
            <div class="item-sub">{{ itemSub(cat, item) }}</div>
          </div>
        </div>
        <div class="panel-footer" @mousedown.prevent="jumpAll">
          在「{{ keyword }}」中搜索全部结果
        </div>
      </template>
      <div v-else-if="!loading" class="search-empty">未找到与 “{{ keyword }}” 相关的结果</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import request from '@/api/request'

const router = useRouter()
const wrapRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const keyword = ref('')
const results = ref<Record<string, any[]>>({})
const loading = ref(false)
const panelVisible = ref(false)

let debounceTimer: number | undefined

const categories = [
  { key: 'users', label: '用户', path: '/users' },
  { key: 'roles', label: '角色', path: '/roles' },
  { key: 'permissions', label: '权限', path: '/permissions' },
  { key: 'apps', label: '开放平台应用', path: '/apps' },
  { key: 'files', label: '文件', path: '/files' },
  { key: 'notices', label: '通知', path: '/system-notification' },
  { key: 'announcements', label: '公告', path: '/announcements' },
] as const

const visibleCategories = computed(() =>
  categories.filter((c) => (results.value[c.key] || []).length > 0)
)
const hasResults = computed(() => visibleCategories.value.length > 0)

function onInput() {
  window.clearTimeout(debounceTimer)
  const kw = keyword.value.trim()
  if (!kw) {
    panelVisible.value = false
    results.value = {}
    return
  }
  panelVisible.value = true
  debounceTimer = window.setTimeout(fetchSearch, 300)
}

async function fetchSearch() {
  const kw = keyword.value.trim()
  if (!kw) return
  loading.value = true
  try {
    const res = await request.get('/search', { params: { keyword: kw, limit: 5 } })
    results.value = res.data || {}
  } catch (e) {
    results.value = {}
  } finally {
    loading.value = false
  }
}

function itemTitle(cat: (typeof categories)[number], item: any): string {
  switch (cat.key) {
    case 'users':
      return item.name || item.username
    case 'roles':
      return item.role_name
    case 'permissions':
      return item.perm_name
    case 'apps':
      return item.name
    case 'notices':
      return item.title
    case 'announcements':
      return item.title
    default:
      return item.original_name
  }
}

function itemSub(cat: (typeof categories)[number], item: any): string {
  switch (cat.key) {
    case 'users':
      return `${item.username} · ${item.email || ''}`
    case 'roles':
      return item.role_code
    case 'permissions':
      return item.perm_code
    case 'apps':
      return item.app_id
    case 'notices':
      return noticeTypeLabel(item.notice_type) + ' · ' + noticeStatusLabel(item.status)
    case 'announcements':
      return announcementStatusLabel(item.status) + ' · ' + announcementPositionLabel(item.position)
    default:
      return item.folder || (item.extension ? item.extension.toUpperCase() : '')
  }
}

function noticeTypeLabel(type: string): string {
  return type === 'maintenance' ? '系统维护' : '系统通知'
}

function noticeStatusLabel(status: string): string {
  return status === 'withdrawn' ? '已撤回' : '已发布'
}

function announcementStatusLabel(status: string): string {
  return status === 'published' ? '已发布' : status === 'unpublished' ? '已下架' : '草稿'
}

function announcementPositionLabel(position: string): string {
  return position === 'banner' ? '首页横幅' : '首页板块'
}

function goTo(cat: (typeof categories)[number], item: any) {
  jumpTo(cat.path)
}

function jumpFirst() {
  const first = visibleCategories.value[0]
  if (first) jumpTo(first.path)
}

function jumpAll() {
  const first = visibleCategories.value[0]
  if (first) jumpTo(first.path)
}

function jumpTo(path: string) {
  const kw = keyword.value.trim()
  if (!kw) return
  router.push({ path, query: { keyword: kw } })
  keyword.value = ''
  results.value = {}
  panelVisible.value = false
}

function closePanel() {
  panelVisible.value = false
  inputRef.value?.blur()
}

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  return !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)
}

function onGlobalKeydown(e: KeyboardEvent) {
  if (e.key === '/' && !isTypingTarget(e.target)) {
    e.preventDefault()
    inputRef.value?.focus()
    inputRef.value?.select()
  }
}

function onClickOutside(e: MouseEvent) {
  if (wrapRef.value && !wrapRef.value.contains(e.target as Node)) {
    panelVisible.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  document.addEventListener('mousedown', onClickOutside)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  document.removeEventListener('mousedown', onClickOutside)
  window.clearTimeout(debounceTimer)
})
</script>

<style scoped>
.search {
  position: relative;
  margin-right: 16px;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  width: 340px;
  height: 40px;
  padding: 0 14px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  background: #fff;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-input-wrap:focus-within {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.12);
}

.search-icon {
  color: #909399;
  font-size: 16px;
  margin-right: 8px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: #303133;
}

.search-input::placeholder {
  color: #a8abb2;
}

.kbd {
  flex-shrink: 0;
  display: inline-block;
  padding: 0 7px;
  height: 22px;
  line-height: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 5px;
  background: #f7f8fa;
  color: #909399;
  font-size: 12px;
  font-family: inherit;
}

.search-panel {
  position: absolute;
  top: 48px;
  right: 0;
  width: 380px;
  max-height: 480px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14);
  z-index: 3000;
  padding: 6px 0;
}

.search-group + .search-group {
  border-top: 1px solid #f0f0f0;
}

.group-title {
  padding: 8px 14px 4px;
  font-size: 12px;
  color: #909399;
  font-weight: 600;
}

.group-item {
  padding: 7px 14px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.group-item:hover {
  background: #f5f7fa;
}

.item-main {
  font-size: 13px;
  color: #303133;
  line-height: 1.4;
}

.item-sub {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.panel-footer {
  padding: 8px 14px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #409eff;
  cursor: pointer;
  text-align: center;
}

.panel-footer:hover {
  background: #f5f7fa;
}

.search-empty {
  padding: 30px 16px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
</style>
