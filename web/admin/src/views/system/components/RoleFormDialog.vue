<template>
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新建角色'" width="600px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="名称" prop="role_name">
        <el-input v-model="form.role_name" />
      </el-form-item>
      <el-form-item v-if="!isEdit" label="编码" prop="role_code">
        <el-input v-model="form.role_code" placeholder="如 auditor" />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="权限">
        <GroupCheckboxPanel :groups="permissionGroups" v-model="selectedPermissions" />
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
import { createRole, updateRole, listRolePermissions, bindRolePermission, unbindRolePermission } from '@/api/role'
import { listPermissions } from '@/api/permission'
import GroupCheckboxPanel, { type GroupCheckboxGroup } from '@/components/GroupCheckboxPanel.vue'
import type { RoleItem, PermissionItem } from '@/types/role'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** create=新建 / edit=编辑 */
  mode: 'create' | 'edit'
  /** 编辑时的原记录 */
  record?: RoleItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 提交成功（调用方负责刷新列表与关闭） */
  submitted: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const isEdit = computed(() => props.mode === 'edit')
const form = ref({ role_name: '', role_code: '', description: '' })
const selectedPermissions = ref<number[]>([])
const permissionList = ref<PermissionItem[]>([])
const formRef = ref<FormInstance>()

/** 表单校验规则（role_code 仅新建时渲染，编辑时不触发） */
const rules: FormRules<{ role_name: string; role_code: string; description: string }> = {
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  role_code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
  description: [{ required: true, message: '请输入角色描述', trigger: 'blur' }],
}

const groupedPermissions = computed(() => {
  const groups: Record<string, PermissionItem[]> = {}
  for (const p of permissionList.value) {
    const mod = p.module || '其他'
    if (!groups[mod]) groups[mod] = []
    groups[mod].push(p)
  }
  return groups
})

// 供共享分组勾选面板消费：模块 → 组，权限 → 选项
const permissionGroups = computed<GroupCheckboxGroup[]>(() =>
  Object.entries(groupedPermissions.value).map(([module, items]) => ({
    label: items[0]?.module_label || module,
    items: items.map(p => ({ value: p.id, label: `${p.perm_name}（${p.perm_code}）` })),
  })),
)

/** 打开弹窗时初始化表单与权限选项 */
watch(
  () => props.visible,
  v => {
    if (!v) return
    void fetchPermissions()
    if (props.mode === 'edit' && props.record) {
      form.value = { role_name: props.record.role_name, role_code: '', description: props.record.description || '' }
      void loadRolePermissions(props.record.id)
    } else {
      form.value = { role_name: '', role_code: '', description: '' }
      selectedPermissions.value = []
    }
  },
)

async function fetchPermissions() {
  const res = await listPermissions({ page: 1, page_size: 200 })
  permissionList.value = res.data.items.filter(p => !p.is_deprecated)
}

/** 编辑模式：回填角色已有权限 */
async function loadRolePermissions(roleId: number) {
  try {
    const res = await listRolePermissions(roleId)
    selectedPermissions.value = res.data.map(p => p.permission.id)
  } catch {
    selectedPermissions.value = []
  }
}

async function handleSubmit() {
  try {
    // 名称/编码/描述必填校验（失败时表单内联提示，不发起请求）
    await formRef.value?.validate()
  } catch {
    return
  }
  // 权限面板非 el-form 字段，保持显式校验
  if (selectedPermissions.value.length === 0) {
    ElMessage.warning('请至少选择一个权限')
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
    const res = await createRole(form.value)
    const roleId = res.data.id
    for (const permId of selectedPermissions.value) {
      await bindRolePermission(roleId, permId)
    }
    ElMessage.success('创建成功')
    emit('submitted')
  } catch {
    // 错误已处理
  }
}

async function handleUpdate() {
  if (!props.record) return
  const roleId = props.record.id
  try {
    // 更新基本信息
    await updateRole(roleId, {
      role_name: form.value.role_name,
      description: form.value.description,
    })
    // 对比权限：先解绑不在新列表里的，再绑定新的
    const currentPerms = selectedPermissions.value
    const oldRes = await listRolePermissions(roleId)
    const oldPerms = oldRes.data.map(p => p.permission.id)
    // 解绑旧的
    for (const pid of oldPerms) {
      if (!currentPerms.includes(pid)) {
        await unbindRolePermission(roleId, pid)
      }
    }
    // 绑定新的
    for (const pid of currentPerms) {
      if (!oldPerms.includes(pid)) {
        await bindRolePermission(roleId, pid)
      }
    }
    ElMessage.success('更新成功')
    emit('submitted')
  } catch {
    // 错误已处理
  }
}
</script>
