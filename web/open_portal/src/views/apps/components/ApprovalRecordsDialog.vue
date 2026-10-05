<template>
  <el-dialog
    :model-value="visible"
    :title="`审批记录 - ${record?.name || ''}`"
    width="820px"
    destroy-on-close
    @update:model-value="emit('update:visible', $event)"
  >
    <div v-loading="loading">
      <div v-if="records.length === 0 && !loading" class="hj-empty">暂无审批记录</div>
      <el-timeline v-else>
        <el-timeline-item
          v-for="r in records"
          :key="r.id"
          :type="timelineType(r.status)"
          :timestamp="formatDateTime(r.created_at)"
          placement="top"
        >
          <el-card shadow="never" class="approval-card">
            <div class="approval-card-head">
              <span class="approval-type">{{ r.registration_type === 'create' ? '创建申请' : '修改申请' }}</span>
              <span class="approval-id">申请码：{{ r.registration_code || `#${r.id}` }}</span>
              <el-tag :type="statusTagType(r.status)" effect="light">{{ statusLabel(r.status) }}</el-tag>
            </div>
            <div class="approval-row">
              <span class="row-label">申请内容</span>
              <span class="row-value">{{ r.registration_type === 'create' ? '创建应用' : '调整应用信息 / 权限范围' }}</span>
            </div>
            <div class="approval-row">
              <span class="row-label">权限范围</span>
              <span class="row-value">
                <el-tag v-for="s in r.scopes" :key="s" size="small" class="hj-mr-4">
                  {{ scopeNameOf(s) === s ? s : `${scopeNameOf(s)}（${s}）` }}
                </el-tag>
                <span v-if="r.scopes.length === 0">-</span>
              </span>
            </div>
            <div v-if="r.reason" class="approval-row">
              <span class="row-label">申请说明</span>
              <span class="row-value">{{ r.reason }}</span>
            </div>
            <div v-if="r.approver_name" class="approval-row">
              <span class="row-label">审批人</span>
              <span class="row-value">{{ r.approver_name }}</span>
            </div>
            <div v-if="r.note" class="approval-row">
              <span class="row-label">审批意见</span>
              <span class="row-value">{{ r.note }}</span>
            </div>
            <div v-if="r.reviewed_at" class="approval-row">
              <span class="row-label">审批时间</span>
              <span class="row-value">{{ formatDateTime(r.reviewed_at) }}</span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
    <template #footer>
      <el-button @click="emit('update:visible', false)">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { formatDateTime } from '@/utils/format'
import { listAppApprovals } from '@/api/apps'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { OpenAppApproval, OpenAppItem } from '@/types/app'

const props = defineProps<{ visible: boolean; record: OpenAppItem | null }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const loading = ref(false)
const records = ref<OpenAppApproval[]>([])

function statusLabel(status: string): string {
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '待审批'
}

function statusTagType(status: string): 'success' | 'danger' | 'warning' | 'info' {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

function timelineType(status: string): 'primary' | 'success' | 'danger' | 'warning' {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

watch(
  () => props.visible,
  async v => {
    if (!v || !props.record) return
    // scope 中文名映射（失败回退为裸编码）
    void fetchScopes()
    loading.value = true
    records.value = []
    try {
      const res = await listAppApprovals(props.record.id)
      records.value = res.data ?? []
    } catch {
      // 错误已处理
    } finally {
      loading.value = false
    }
  },
)
</script>

<style scoped>
.hj-empty {
  text-align: center;
  color: var(--hj-text-secondary);
  padding: 40px 0;
}
.approval-card {
  border: 1px solid var(--hj-border-lighter);
  border-radius: 8px;
  margin-bottom: 4px;
}
.approval-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.approval-type {
  font-size: 14px;
  font-weight: 600;
  color: var(--hj-primary);
}
.approval-id {
  font-size: 12px;
  color: var(--hj-text-secondary);
}
.approval-row {
  display: flex;
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
}
.row-label {
  flex-shrink: 0;
  width: 76px;
  color: var(--hj-text-secondary);
}
.row-value {
  color: var(--hj-text-body);
  word-break: break-all;
}
</style>
