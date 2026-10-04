<template>
  <el-table :data="rows" class="doc-table" :header-cell-style="headerStyle" :cell-style="cellStyle" row-key="name">
    <!-- 位置列（仅 Query/Path 场景） -->
    <el-table-column v-if="showLoc" label="位置" width="86">
      <template #default="{ row }">
        <span class="loc-tag" :class="row.__loc === 'path' ? 'loc-path' : 'loc-query'">
          {{ row.__loc }}
        </span>
      </template>
    </el-table-column>
    <el-table-column :label="nameLabel" min-width="170">
      <template #default="{ row }">
        <span class="param-name">{{ row.name }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="type" label="参数类型" min-width="110">
      <template #default="{ row }">
        <code class="type-code">{{ row.type }}</code>
      </template>
    </el-table-column>
    <el-table-column label="是否必填" width="96">
      <template #default="{ row }">
        <span class="req-badge" :class="row.required ? 'req-yes' : 'req-no'">
          {{ row.required ? '必填' : '可选' }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="可选值" min-width="120">
      <template #default="{ row }">
        <span :class="{ 'text-muted': row.values === '-' }">{{ row.values ?? '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="限制" min-width="140">
      <template #default="{ row }">
        <span :class="{ 'text-muted': row.limit === '-' }">{{ row.limit ?? '-' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="示例" min-width="150">
      <template #default="{ row }">
        <code class="example-code">{{ row.example ?? '-' }}</code>
      </template>
    </el-table-column>
    <el-table-column label="描述" min-width="200">
      <template #default="{ row }">
        <span class="desc-text">{{ row.desc }}</span>
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
const cellStyle = {
  padding: '12px 16px',
  fontSize: '13px',
}
</script>

<style scoped>
.doc-table {
  width: 100%;
  --el-table-border-color: #ebeef5;
  --el-table-header-bg-color: #f7f8fa;
  --el-table-row-hover-bg-color: #f5f9ff;
}
.doc-table :deep(th.el-table__cell) {
  border-bottom: 1px solid #ebeef5;
}
.doc-table :deep(td.el-table__cell) {
  border-bottom: 1px solid #f2f3f5;
  color: #606266;
}
.param-name {
  color: #303133;
  font-weight: 600;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12.5px;
}
.type-code {
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  color: #7c3aed;
  background: #f6f4fe;
  padding: 1px 6px;
  border-radius: 4px;
}
.example-code {
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 4px;
  word-break: break-all;
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
  color: #909399;
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
  color: #409eff;
  background: #ecf5ff;
}
.loc-path {
  color: #e6a23c;
  background: #fdf6ec;
}
.text-muted {
  color: #c0c4cc;
}
.desc-text {
  color: #606266;
  line-height: 1.7;
}
</style>
