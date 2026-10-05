<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand" :title="collapsed ? '展开菜单' : '折叠菜单'" @click="$emit('toggle')">
      <el-icon class="brand-icon" :size="22"><Connection /></el-icon>
      <span v-show="!collapsed" class="brand-text">汉江开放平台</span>
    </div>

    <el-menu :default-active="activePath" router class="side-menu" :collapse="collapsed">
      <el-menu-item index="/home">
        <el-icon><HomeFilled /></el-icon>
        <template #title>首页</template>
      </el-menu-item>
      <el-menu-item index="/apps">
        <el-icon><Grid /></el-icon>
        <template #title>应用管理</template>
      </el-menu-item>

      <!-- 开放能力：模块（二级）→ 具体接口（三级） -->
      <el-sub-menu index="/capability">
        <template #title>
          <el-icon><Document /></el-icon>
          <span>开放能力</span>
        </template>
        <el-sub-menu v-for="mod in capabilityModules" :key="mod.key" :index="`/capability/${mod.key}`">
          <template #title>
            <span class="cap-module-name">{{ mod.name }}</span>
            <span class="cap-module-count">{{ mod.apis.length }}</span>
          </template>
          <el-menu-item v-for="api in mod.apis" :key="api.id" :index="`/capability/${mod.key}/${api.id}`">
            <span class="cap-method" :class="methodClass(api.method)">{{ api.method }}</span>
            <template #title>
              <span class="cap-api-name">{{ api.name }}</span>
            </template>
          </el-menu-item>
        </el-sub-menu>
      </el-sub-menu>

      <el-sub-menu index="/auth">
        <template #title>
          <el-icon><Lock /></el-icon>
          <span>认证和授权</span>
        </template>
        <el-menu-item index="/auth/signature">
          <template #title>签名说明</template>
        </el-menu-item>
        <el-menu-item index="/auth/params">
          <template #title>通用参数</template>
        </el-menu-item>
        <el-menu-item index="/auth/errors">
          <template #title>通用错误码</template>
        </el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <template #title>个人中心</template>
      </el-menu-item>
    </el-menu>

    <div class="collapse-btn" @click="$emit('toggle')">
      <el-icon :size="16"><Fold /></el-icon>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { HomeFilled, Lock } from '@element-plus/icons-vue'
import { capabilityModules } from '@/data/capability'
import type { CapabilityApi } from '@/types/capability'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const route = useRoute()

// 侧边栏按完整路由路径高亮（支持二级/三级菜单：/capability/user/user-create 命中三级菜单项）
const activePath = computed(() => route.path)

const METHOD_CLASS: Record<CapabilityApi['method'], string> = {
  GET: 'm-get',
  POST: 'm-post',
  PATCH: 'm-patch',
  DELETE: 'm-delete',
}

function methodClass(method: CapabilityApi['method']): string {
  return METHOD_CLASS[method]
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 220px;
  background: var(--hj-bg-card);
  border-right: 1px solid var(--hj-border-lighter);
  transition: width 0.2s;
}
.sidebar.collapsed {
  width: 64px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--hj-border-lighter);
  background: linear-gradient(90deg, #f6faff 0%, #ffffff 100%);
  flex-shrink: 0;
  transition: background 0.15s ease;
  user-select: none;
}
.brand:hover {
  background: linear-gradient(90deg, var(--hj-primary-bg) 0%, #ffffff 100%);
}
.sidebar.collapsed .brand {
  justify-content: center;
  padding: 0;
}
.brand-icon {
  color: var(--hj-primary);
  flex-shrink: 0;
  filter: drop-shadow(0 1px 2px rgba(64, 158, 255, 0.4));
}
.brand-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--hj-text-title);
  white-space: nowrap;
  letter-spacing: 0.3px;
}
.side-menu {
  flex: 1;
  border-right: none;
  padding: 8px 0;
}
/* 菜单项：激活态品牌蓝渐变左条 + 淡蓝底 */
.side-menu :deep(.el-menu-item),
.side-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: 8px;
  color: var(--hj-text-body);
  font-size: 13.5px;
  transition: background 0.15s ease, color 0.15s ease;
}
.side-menu :deep(.el-menu-item:hover),
.side-menu :deep(.el-sub-menu__title:hover) {
  background: var(--hj-bg-hover);
  color: var(--hj-primary);
}
.side-menu :deep(.el-menu-item.is-active) {
  background: var(--hj-primary-bg);
  color: var(--hj-primary);
  font-weight: 600;
}
.side-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 2px;
  background: var(--hj-primary);
}
/* 折叠态下悬浮子菜单背景统一 */
.side-menu :deep(.el-menu--popup) {
  border-radius: 10px;
  padding: 4px;
}
/* 三级菜单：模块名 + 接口数角标 */
.cap-module-name {
  font-size: 13px;
}
.cap-module-count {
  float: right;
  margin-left: 8px;
  font-size: 11px;
  color: var(--hj-text-secondary);
  background: var(--hj-border-lighter);
  border-radius: 8px;
  padding: 0 6px;
  line-height: 16px;
}
/* 三级菜单：HTTP 方法色标 + 接口名 */
.cap-method {
  display: inline-block;
  width: 34px;
  margin-right: 6px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  text-align: center;
  line-height: 16px;
  border-radius: 3px;
  flex-shrink: 0;
}
.m-get { background: #67c23a; }
.m-post { background: var(--hj-primary); }
.m-patch { background: #e6a23c; }
.m-delete { background: #f56c6c; }
.cap-api-name {
  font-size: 13px;
}
.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  border-top: 1px solid var(--hj-border-lighter);
  color: var(--hj-text-secondary);
  cursor: pointer;
  transition: color 0.2s;
}
.collapse-btn:hover {
  color: var(--hj-primary);
  background: var(--hj-bg-hover);
}
</style>
