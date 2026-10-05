<template>
  <el-table :data="rows" class="doc-table" :header-cell-style="headerStyle" row-key="name">
    <!-- 位置列（仅 Query/Path 场景） -->
    <el-table-column v-if="showLoc" label="位置" width="82">
      <template #default="{ row }">
        <span class="loc-tag" :class="row.__loc === 'path' ? 'loc-path' : 'loc-query'">
          {{ row.__loc }}
        </span>
      </template>
    </el-table-column>
    <el-table-column :label="nameLabel" min-width="180">
      <template #default="{ row }">
        <span class="param-name">{{ row.name }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="type" label="类型" min-width="110">
      <template #default="{ row }">
        <code class="type-code">{{ row.type }}</code>
      </template>
    </el-table-column>
    <el-table-column label="必填" width="88">
      <template #default="{ row }">
        <span class="req-badge" :class="row.required ? 'req-yes' : 'req-no'">
          {{ row.required ? '必填' : '可选' }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="说明" min-width="320">
      <template #default="{ row }">
        <div class="desc-cell">
          <span class="desc-text">{{ row.desc }}</span>
          <span v-if="row.values && row.values !== '-'" class="desc-extra">
            可选值：<code>{{ row.values }}</code>
          </span>
          <span v-if="row.limit && row.limit !== '-'" class="desc-extra">
            限制：<code>{{ row.limit }}</code>
          </span>
          <span v-if="row.example && row.example !== '-'" class="desc-extra">
            示例：<code>{{ row.example }}</code>
          </span>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { ApiParamRow } from '@/types/capability'

defineProps<{
  /** 行数据（Query/Path 合并场景可携带 __loc 标记） */
  rows: Array<ApiParamRow & { __loc?: 'query' | 'path' }>
  /** 首列表头（Header 名称 / 属性名 / 参数名称） */
  nameLabel: string
  /** 是否展示"位置"列（Query/Path 合并表用） */
  showLoc?: boolean
}>()

// WPS 风格：浅灰表头 + 宽松行高
const headerStyle = {
  background: '#f7f8fa',
  color: '#303133',
  fontWeight: 600,
  fontSize: '13px',
  padding: '12px 16px',
}
</script>

<style scoped>
.doc-table {
  width: 100%;
  --el-table-border-color: var(--hj-border-light);
  --el-table-header-bg-color: var(--hj-bg-page);
  --el-table-row-hover-bg-color: var(--hj-bg-hover);
}
.doc-table :deep(th.el-table__cell) {
  border-bottom: 1px solid var(--hj-border-light);
}
.doc-table :deep(td.el-table__cell) {
  border-bottom: 1px solid var(--hj-border-lighter);
  color: var(--hj-text-regular);
  vertical-align: top;
}
.param-name {
  color: var(--hj-text-title);
  font-weight: 600;
  font-family: var(--hj-font-mono);
  font-size: 12.5px;
  word-break: break-all;
}
.type-code {
  font-family: var(--hj-font-mono);
  font-size: 12px;
  color: #7c3aed;
  background: #f6f4fe;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.req-badge {
  display: inline-block;
  min-width: 40px;
  text-align: center;
  font-size: 12px;
  line-height: 20px;
  border-radius: 10px;
  padding: 0 8px;
}
.req-yes {
  color: #f56c6c;
  background: #fef0f0;
}
.req-no {
  color: var(--hj-text-secondary);
  background: #f4f4f5;
}
.loc-tag {
  display: inline-block;
  min-width: 44px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  border-radius: 4px;
  text-transform: uppercase;
}
.loc-query {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
}
.loc-path {
  color: #e6a23c;
  background: #fdf6ec;
}
/* ─── 说明列：主描述 + 追加信息（可选值/限制/示例），紧凑展示 ─── */
.desc-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.desc-text {
  color: var(--hj-text-regular);
  line-height: 1.65;
}
.desc-extra {
  display: inline-block;
  font-size: 12px;
  color: var(--hj-text-secondary);
  line-height: 1.6;
}
.desc-extra code {
  font-family: var(--hj-font-mono);
  font-size: 12px;
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  padding: 0 5px;
  border-radius: 3px;
  word-break: break-all;
}
</style>
