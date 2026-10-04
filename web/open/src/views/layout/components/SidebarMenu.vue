<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand" @click="router.push('/home')">
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
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled, Lock } from '@element-plus/icons-vue'
import { capabilityModules } from '@/data/capability'
import type { CapabilityApi } from '@/types/capability'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const route = useRoute()
const router = useRouter()

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
  background: #fff;
  border-right: 1px solid #eef0f4;
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
  border-bottom: 1px solid #f0f2f5;
}
.brand-icon {
  color: #409eff;
  flex-shrink: 0;
}
.brand-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}
.side-menu {
  flex: 1;
  border-right: none;
}
/* 三级菜单：模块名 + 接口数角标 */
.cap-module-name {
  font-size: 13px;
}
.cap-module-count {
  float: right;
  margin-left: 8px;
  font-size: 11px;
  color: #909399;
  background: #f0f2f5;
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
.m-post { background: #409eff; }
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
  border-top: 1px solid #f0f2f5;
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}
.collapse-btn:hover {
  color: #409eff;
}
</style>
