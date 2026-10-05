<template>
  <div class="page-head">
    <div class="crumbs">{{ crumbs }}</div>
    <h1 class="page-title">{{ title }}</h1>
    <p class="page-desc">{{ desc }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  /** 面包屑（如：开放能力 / 用户管理） */
  crumbs: string
  /** 页面标题 */
  title: string
  /** 页面简介（可空） */
  desc?: string
}>()
</script>

<style scoped>
.page-head {
  margin-bottom: 20px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--hj-border-light);
}
.crumbs {
  font-size: 12px;
  color: var(--hj-text-secondary);
  margin-bottom: 8px;
  letter-spacing: 0.3px;
}
.page-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--hj-text-title);
  letter-spacing: 0.5px;
}
.page-desc {
  margin: 0;
  font-size: 13px;
  color: var(--hj-text-secondary);
  line-height: 1.7;
}
</style>
