<template>
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑应用' : '新建应用'" width="640px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="鉴权模式" prop="auth_mode">
        <el-select v-model="form.auth_mode" class="hj-w-full">
          <el-option label="明文 (plain)" value="plain" />
          <el-option label="HMAC 签名 (hmac)" value="hmac" />
          <el-option label="双模式 (both)" value="both" />
        </el-select>
      </el-form-item>
      <el-form-item label="权限范围">
        <GroupCheckboxPanel :groups="scopeGroups" v-model="form.scopes" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { listScopes, createApp, updateApp } from '@/api/openapi'
import GroupCheckboxPanel, { type GroupCheckboxGroup } from '@/components/GroupCheckboxPanel.vue'
import type { OpenAppItem, OpenScope, OpenAppFormPayload } from '@/types/openapi'

/** 创建成功时携带的新密钥（父级用于展示结果弹窗） */
export interface AppSecret {
  app_id: string
  app_key: string
}

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** create=新建 / edit=编辑 */
  mode: 'create' | 'edit'
  /** 编辑时的原记录 */
  record?: OpenAppItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 编辑提交成功（父级刷新列表） */
  submitted: []
  /** 创建提交成功（父级刷新列表并展示密钥） */
  created: [secret: AppSecret]
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const isEdit = computed(() => props.mode === 'edit')
const form = ref<OpenAppFormPayload>({ name: '', description: '', auth_mode: 'plain', scopes: [] })
const scopeList = ref<OpenScope[]>([])
const formRef = ref<FormInstance>()

/** 表单校验规则（名称/描述/鉴权模式必填；权限范围在提交时显式校验） */
const rules: FormRules<OpenAppFormPayload> = {
  name: [{ required: true, message: '请输入应用名称', trigger: 'blur' }],
  description: [{ required: true, message: '请输入应用描述', trigger: 'blur' }],
  auth_mode: [{ required: true, message: '请选择鉴权模式', trigger: 'change' }],
}

const groupedScopes = computed(() => {
  const groups: Record<string, OpenScope[]> = {}
  for (const s of scopeList.value) {
    const mod = s.module || '其他'
    if (!groups[mod]) groups[mod] = []
    groups[mod].push(s)
  }
  return groups
})

// 供共享分组勾选面板消费：模块 → 组，scope → 选项
const scopeGroups = computed<GroupCheckboxGroup[]>(() =>
  Object.entries(groupedScopes.value).map(([module, items]) => ({
    label: items[0]?.module_label || module,
    items: items.map(s => ({ value: s.scope_code, label: `${s.scope_name}（${s.scope_code}）` })),
  })),
)

/** 打开弹窗时初始化表单与 scope 选项 */
watch(
  () => props.visible,
  v => {
    if (!v) return
    void fetchScopes()
    if (props.mode === 'edit' && props.record) {
      form.value = {
        name: props.record.name,
        description: props.record.description || '',
        auth_mode: props.record.auth_mode,
        scopes: [...props.record.scopes],
      }
    } else {
      form.value = { name: '', description: '', auth_mode: 'plain', scopes: [] }
    }
  },
)

async function fetchScopes() {
  const res = await listScopes()
  scopeList.value = res.data
}

async function handleSubmit() {
  try {
    // 名称/描述/鉴权模式必填校验（失败时表单内联提示，不发起请求）
    await formRef.value?.validate()
  } catch {
    return
  }
  // 权限范围面板非 el-form 字段，保持显式校验（创建/编辑统一至少 1 个）
  if (form.value.scopes.length === 0) {
    ElMessage.warning('请至少勾选一个权限范围')
    return
  }
  if (isEdit.value) {
    await handleUpdate()
  } else {
    await handleCreate()
  }
}

async function handleCreate() {
  try {
    const res = await createApp(form.value)
    emit('created', { app_id: res.data.app_id, app_key: res.data.app_key })
  } catch {
    // 错误已处理
  }
}

async function handleUpdate() {
  if (!props.record) return
  try {
    await updateApp(props.record.id, {
      name: form.value.name,
      description: form.value.description,
      auth_mode: form.value.auth_mode,
      scopes: form.value.scopes,
    })
    ElMessage.success('更新成功')
    emit('submitted')
  } catch {
    // 错误已处理
  }
}
</script>
