<template>
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新建用户'" width="500px">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item v-if="!isEdit" label="用户名" prop="username">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="生日" prop="birthday">
        <el-date-picker v-model="form.birthday" type="date" value-format="YYYY-MM-DD" placeholder="选择生日" />
      </el-form-item>
      <el-form-item label="性别" prop="gender">
        <el-radio-group v-model="form.gender">
          <el-radio value="male">男</el-radio>
          <el-radio value="female">女</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="角色" prop="role_ids">
        <el-select v-model="form.role_ids" multiple class="hj-w-full">
          <el-option v-for="r in roles" :key="r.id" :label="r.role_name" :value="r.id">
            <span style="float: left">{{ r.role_name }}</span>
            <el-tag v-if="r.role_type === 'system'" size="small" type="warning" style="float: right; margin-left: 10px"
              >系统内置</el-tag
            >
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item v-if="!isEdit" label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio value="enabled">启用</el-radio>
          <el-radio value="disabled">禁用</el-radio>
        </el-radio-group>
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
import { createUser, updateUser } from '@/api/user'
import { listRoles } from '@/api/role'
import type { UserItem, UserFormPayload } from '@/types/user'
import type { RoleItem } from '@/types/role'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** create=新建 / edit=编辑 */
  mode: 'create' | 'edit'
  /** 编辑时的原记录 */
  record?: UserItem | null
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
const editId = ref(0)
const roles = ref<RoleItem[]>([])
const formRef = ref<FormInstance>()

/** 表单校验规则（新建/编辑共用；username/password 仅新建时渲染，编辑时不触发） */
const rules: FormRules<UserFormPayload> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: ['blur', 'change'] },
  ],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  birthday: [{ required: true, message: '请选择生日', trigger: 'change' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  role_ids: [
    {
      required: true,
      type: 'array',
      min: 1,
      message: '请至少选择一个角色',
      trigger: 'change',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度须为 8-64 位', trigger: 'blur' },
  ],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const form = ref<UserFormPayload>({
  username: '',
  name: '',
  email: '',
  phone: '',
  birthday: '',
  gender: 'male',
  role_ids: [],
  password: '',
  status: 'enabled',
})

/** 打开弹窗时按模式初始化表单并加载角色选项 */
watch(
  () => props.visible,
  v => {
    if (!v) return
    editId.value = props.record?.id ?? 0
    if (props.mode === 'edit' && props.record) {
      form.value = {
        username: props.record.username,
        name: props.record.name || '',
        email: props.record.email || '',
        phone: props.record.phone || '',
        birthday: props.record.birthday ? props.record.birthday.split('T')[0] : '',
        gender: props.record.gender || 'male',
        role_ids: props.record.roles ? props.record.roles.map(r => r.id) : [],
        password: '',
        status: props.record.status,
      }
    } else {
      form.value = {
        username: '',
        name: '',
        email: '',
        phone: '',
        birthday: '',
        gender: 'male',
        role_ids: [],
        password: '',
        status: 'enabled',
      }
    }
    void fetchRoles()
  },
)

async function fetchRoles() {
  try {
    const res = await listRoles()
    roles.value = Array.isArray(res.data) ? res.data : res.data.items
    const adminRole = roles.value.find(r => r.role_code === 'admin')
    // 新建时默认选中 admin 角色（与后端默认角色语义一致）
    if (adminRole && !isEdit.value) form.value.role_ids = [adminRole.id]
  } catch {
    // 错误已处理
  }
}

async function handleSubmit() {
  try {
    // 前端必填/格式校验（失败时表单内联展示错误，不发起请求）
    await formRef.value?.validate()
  } catch {
    return
  }
  try {
    if (isEdit.value) {
      const { name, email, phone, birthday, gender, role_ids, status } = form.value
      const birthdayStr = birthday ? (typeof birthday === 'string' ? birthday.split('T')[0] : '') : ''
      await updateUser(editId.value, { name, email, phone, birthday: birthdayStr, gender, role_ids, status })
      ElMessage.success('更新成功')
    } else {
      // 创建时直接提交多角色 role_ids（后端 UserCreateRequest 已支持）
      await createUser({ ...form.value, role_ids: form.value.role_ids })
      ElMessage.success('创建成功')
    }
    emit('submitted')
  } catch {
    // 错误已处理
  }
}
</script>
