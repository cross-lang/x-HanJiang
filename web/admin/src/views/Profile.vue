<template>
  <div style="max-width: 800px; margin: 0 auto">
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px">
        <el-avatar :size="64" style="background: #79bbff; font-size: 28px">
          {{ (userStore.userInfo?.name || 'U').charAt(0) }}
        </el-avatar>
        <div>
          <h2 style="margin: 0">{{ userStore.userInfo?.name || userStore.userInfo?.username }}</h2>
          <p style="margin: 5px 0 0; color: #999">@{{ userStore.userInfo?.username }}</p>
        </div>
      </div>

      <el-divider />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <el-form :model="form" label-width="80px" style="max-width: 500px">
            <el-form-item label="用户名">
              <el-input :model-value="userStore.userInfo?.username" disabled />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="form.name" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="form.email" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="form.phone" />
            </el-form-item>
            <el-form-item label="生日">
              <el-date-picker v-model="form.birthday" type="date" />
            </el-form-item>
            <el-form-item label="性别">
              <el-radio-group v-model="form.gender">
                <el-radio value="male">男</el-radio>
                <el-radio value="female">女</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveInfo">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="修改密码" name="password">
          <el-form :model="pwdForm" label-width="100px" style="max-width: 500px">
            <el-form-item label="原密码">
              <el-input v-model="pwdForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input v-model="pwdForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="pwdForm.confirm_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="changePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const activeTab = ref('info')

const form = ref({
  name: '',
  email: '',
  phone: '',
  birthday: '',
  gender: 'male',
})

const pwdForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

onMounted(async () => {
  const info = await userStore.fetchUserInfo()
  if (info) {
    form.value = {
      name: info.name || '',
      email: info.email || '',
      phone: info.phone || '',
      birthday: info.birthday || '',
      gender: info.gender || 'male',
    }
  }
})

async function saveInfo() {
  try {
    await request.patch('/auth/me', form.value)
    ElMessage.success('保存成功')
    userStore.fetchUserInfo()
  } catch (e) {
    // 错误已处理
  }
}

async function changePassword() {
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  try {
    await request.post('/auth/change-password', {
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password,
    })
    ElMessage.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (e) {
    // 错误已处理
  }
}
</script>
