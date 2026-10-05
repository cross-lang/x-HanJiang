<template>
  <el-dialog v-model="dialogVisible" :title="readonly ? '申请详情' : '审批应用申请'" width="600px" @closed="resetForm">
    <!-- 申请信息 -->
    <el-descriptions :column="1" border label-width="112px" class="hj-mb-16">
      <el-descriptions-item label="申请码">
        <code class="reg-id-code">{{ record?.registration_code || `#${record?.id}` }}</code>
      </el-descriptions-item>
      <el-descriptions-item label="申请类型">
        <el-tag :type="record?.registration_type === 'create' ? 'primary' : 'warning'" size="small">
          {{ record?.registration_type === 'create' ? '创建申请' : '修改申请' }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="提交时间">
        {{ record?.created_at ? formatDateTime(record.created_at) : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="应用名称">{{ record?.app_name }}</el-descriptions-item>
      <el-descriptions-item label="App ID">
        <code class="app-id-code">{{ record?.app_id_str }}</code>
      </el-descriptions-item>
      <el-descriptions-item label="申请人">{{ record?.owner_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="鉴权模式">
        <el-tag v-if="record?.auth_mode === 'plain'" type="warning" size="small">明文</el-tag>
        <el-tag v-else-if="record?.auth_mode === 'hmac'" type="success" size="small">HMAC 签名</el-tag>
        <el-tag v-else type="primary" size="small">双模式</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="申请 scope">
        <div class="scope-list">
          <el-tag v-for="s in record?.scopes || []" :key="s" size="small" class="hj-mr-4">
            {{ scopeNameOf(s) === s ? s : `${scopeNameOf(s)}（${s}）` }}
          </el-tag>
          <span v-if="!(record?.scopes || []).length" class="hj-text-muted">未申请 scope</span>
        </div>
      </el-descriptions-item>
      <!-- 已审批（终态）记录：只读展示审批结果 -->
      <template v-if="record && record.status !== 'pending'">
        <el-descriptions-item label="审批状态">
          <el-tag :type="record.status === 'approved' ? 'success' : 'danger'" size="small">
            {{ record.status === 'approved' ? '已通过' : '已驳回' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="审批意见">
          {{ record.approval_note || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="审批时间">
          {{ record.approved_at ? formatDateTime(record.approved_at) : '-' }}
        </el-descriptions-item>
      </template>
    </el-descriptions>

    <el-form v-if="isPending && !readonly" ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="审批结论">
        <el-radio-group v-model="form.approved">
          <el-radio-button :value="true">通过</el-radio-button>
          <el-radio-button :value="false">驳回</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="审批意见" prop="note">
        <el-input
          v-model="form.note"
          type="textarea"
          :rows="3"
          maxlength="255"
          show-word-limit
          :placeholder="form.approved ? '选填：可通过的补充说明' : '必填：请说明驳回原因，开发者将据此调整后重新提交'"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <template v-if="isPending && !readonly">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ form.approved ? '确认通过' : '确认驳回' }}
        </el-button>
      </template>
      <el-button v-else type="primary" @click="dialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { reviewAppRegistration } from '@/api/openapi'
import { scopeNameOf } from '@/composables/useScopeCatalog'
import { formatDateTime } from '@/utils/format'
import type { AppRegistrationItem } from '@/types/openapi'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** 待审批的申请（批次） */
  record: AppRegistrationItem | null
  /** 只读详情模式：隐藏审批表单，仅展示申请信息与审批结果 */
  readonly?: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 审批提交成功（父级刷新列表） */
  submitted: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

/** 是否为待审批状态（终态记录仅只读展示，不渲染审批表单） */
const isPending = computed(() => props.record?.status === 'pending')

const form = reactive<{ approved: boolean; note: string }>({ approved: true, note: '' })
const formRef = ref<FormInstance>()
const submitting = ref(false)

const rules: FormRules = {
  note: [
    {
      validator: (_rule, value: string, callback) => {
        if (!form.approved && !value.trim()) {
          callback(new Error('驳回时必须填写审批意见'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

watch(
  () => props.visible,
  v => {
    if (v) {
      form.approved = true
      form.note = ''
    }
  },
)

function resetForm() {
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  if (!props.record || !isPending.value) return
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    await reviewAppRegistration(props.record.id, {
      approved: form.approved,
      note: form.note.trim() || undefined,
    })
    ElMessage.success(form.approved ? '已通过，应用可正常调用开放接口' : '已驳回，开发者可调整后重新提交')
    dialogVisible.value = false
    emit('submitted')
  } catch {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.reg-id-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12.5px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 4px;
}
.app-id-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12.5px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 4px;
  word-break: break-all;
}
.scope-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
:deep(.el-descriptions__label) {
  white-space: nowrap;
}
</style>
