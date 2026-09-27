<template>
  <div style="max-width: 900px; margin: 0 auto">
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

        <el-tab-pane label="角色权限" name="roles">
          <div style="padding: 10px 0">
            <h4 style="margin: 0 0 16px; color: #333">我的角色</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 30px">
              <el-tag v-for="r in roles" :key="r.id" type="primary" size="large" effect="dark" style="padding: 8px 16px; font-size: 14px">
                {{ r.name }}
              </el-tag>
            </div>

            <h4 style="margin: 0 0 16px; color: #333">我的权限</h4>
            <el-alert v-if="permissions.includes('*')" type="success" :closable="false" style="margin-bottom: 16px">
              超级管理员，拥有所有权限
            </el-alert>
            <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px">
              <div v-for="group in groupedPermissions" :key="group.module" style="background: #f8f9fa; border-radius: 8px; padding: 16px">
                <div style="font-weight: 600; color: #409eff; margin-bottom: 12px; font-size: 14px">
                  {{ moduleNameMap[group.module] || group.module }}
                </div>
                <div v-for="p in group.items" :key="p.code" style="padding: 4px 0; font-size: 13px; color: #555">
                  {{ p.name }} <span style="color: #aaa; font-size: 12px">({{ p.code }})</span>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="通知偏好" name="notify">
          <div style="padding: 10px 0">
            <el-alert type="info" :closable="false" style="margin-bottom: 20px">
              选择您希望接收哪些事件的通知，未勾选的将不再推送
            </el-alert>
            <el-table :data="preferenceEvents" border>
              <el-table-column prop="name" label="事件" width="180" />
              <el-table-column v-for="ch in channelList" :key="ch.code" :label="ch.name" width="100" align="center">
                <template #default="{ row }">
                  <el-switch
                    :model-value="row.channels.find((c: any) => c.code === ch.code)?.enabled"
                    @change="(val: string | number | boolean) => toggleChannel(row.event, ch.code, val as boolean)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="安全设置" name="security">
          <div style="max-width: 600px">
            <el-alert type="warning" :closable="false" style="margin-bottom: 20px">
              修改手机号、邮箱、密码均需通过邮箱验证码二次认证
            </el-alert>

            <!-- 手机 -->
            <el-card shadow="never" style="margin-bottom: 16px; background: #fafafa">
              <template #header><b>绑定手机</b></template>
              <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px">
                <span style="color: #666; width: 60px">当前</span>
                <span>{{ userStore.userInfo?.phone || '未绑定' }}</span>
              </div>
              <el-form :model="phoneForm" label-width="80px">
                <el-form-item label="新手机号">
                  <el-input v-model="phoneForm.phone" placeholder="请输入新手机号" />
                </el-form-item>
                <el-form-item label="邮箱验证码">
                  <div style="display: flex; gap: 8px; width: 100%">
                    <el-input v-model="phoneForm.code" placeholder="6 位验证码" style="flex: 1" />
                    <el-button @click="sendCode('phone')" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="updatePhone">修改手机号</el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 邮箱 -->
            <el-card shadow="never" style="margin-bottom: 16px; background: #fafafa">
              <template #header><b>绑定邮箱</b></template>
              <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 12px">
                <span style="color: #666; width: 60px">当前</span>
                <span>{{ userStore.userInfo?.email || '未绑定' }}</span>
              </div>
              <el-form :model="emailForm" label-width="80px">
                <el-form-item label="新邮箱">
                  <el-input v-model="emailForm.email" placeholder="请输入新邮箱" />
                </el-form-item>
                <el-form-item label="邮箱验证码">
                  <div style="display: flex; gap: 8px; width: 100%">
                    <el-input v-model="emailForm.code" placeholder="6 位验证码" style="flex: 1" />
                    <el-button @click="sendCode('email')" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="updateEmail">修改邮箱</el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 密码 -->
            <el-card shadow="never" style="background: #fafafa">
              <template #header><b>修改密码</b></template>
              <el-form :model="pwdForm" label-width="100px">
                <el-form-item label="原密码">
                  <el-input v-model="pwdForm.old_password" type="password" show-password />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input v-model="pwdForm.new_password" type="password" show-password />
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input v-model="pwdForm.confirm_password" type="password" show-password />
                </el-form-item>
                <el-form-item label="邮箱验证码">
                  <div style="display: flex; gap: 8px; width: 100%">
                    <el-input v-model="pwdForm.code" placeholder="6 位验证码" style="flex: 1" />
                    <el-button @click="sendCode('password')" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="changePassword">修改密码</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const activeTab = ref('info')
const roles = ref<any[]>([])
const permissions = ref<string[]>([])
const permissionList = ref<any[]>([])
const preferenceEvents = ref<any[]>([])
const recipients = ref<any[]>([])
const newRecipient = ref({ channel: 'email', recipient: '', label: '' })
const channelNames: Record<string, string> = {
  station: '站内信', email: '邮件', dingtalk: '钉钉', feishu: '飞书',
}

const channelList = [
  { code: 'station', name: '站内信' },
  { code: 'email', name: '邮件' },
  { code: 'dingtalk', name: '钉钉' },
  { code: 'feishu', name: '飞书' },
]

const moduleNameMap: Record<string, string> = {
  user: '用户管理',
  role: '角色管理',
  file: '文件管理',
  audit_log: '审计日志',
  login_log: '登录日志',
  notification: '通知管理',
  alert: '告警管理',
  maintenance: '维护管理',
  openapi_app: '开放平台应用',
  openapi_scope: '开放平台权限',
  dashboard: '仪表盘',
  swagger: 'Swagger文档',
}

const groupedPermissions = computed(() => {
  const map: Record<string, any[]> = {}
  for (const p of permissionList.value) {
    if (!map[p.module]) map[p.module] = []
    map[p.module].push(p)
  }
  return Object.entries(map).map(([module, items]) => ({ module, items }))
})

const form = ref({
  name: '',
  birthday: '',
  gender: 'male',
})

const phoneForm = ref({ phone: '', code: '' })
const emailForm = ref({ email: '', code: '' })
const pwdForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
  code: '',
})

const codeLoading = ref(false)

onMounted(async () => {
  const info = await userStore.fetchUserInfo()
  if (info) {
    form.value = {
      name: info.name || '',
      birthday: info.birthday || '',
      gender: info.gender || 'male',
    }
    roles.value = info.roles || []
    permissions.value = info.permissions || []
    permissionList.value = info.permission_list || []
  }
  try {
    const res = await request.get('/profile/notification-preferences')
    preferenceEvents.value = res.data.events
  } catch (e) { /* ignore */ }
  try {
    const res = await request.get('/profile/notification-recipients')
    recipients.value = res.data.items
  } catch (e) { /* ignore */ }
})

async function sendCode(_target: string) {
  codeLoading.value = true
  try {
    await request.post('/profile/send-verify-code')
    ElMessage.success('验证码已发送至邮箱，5 分钟内有效')
  } catch (e) {
    // 错误已处理
  } finally {
    codeLoading.value = false
  }
}

async function updatePhone() {
  if (!phoneForm.value.phone) {
    ElMessage.warning('请输入新手机号')
    return
  }
  try {
    await request.post('/profile/update-phone', phoneForm.value)
    ElMessage.success('手机号修改成功')
    phoneForm.value = { phone: '', code: '' }
    userStore.fetchUserInfo()
  } catch (e) { /* 错误已处理 */ }
}

async function updateEmail() {
  if (!emailForm.value.email) {
    ElMessage.warning('请输入新邮箱')
    return
  }
  try {
    await request.post('/profile/update-email', emailForm.value)
    ElMessage.success('邮箱修改成功')
    emailForm.value = { email: '', code: '' }
    userStore.fetchUserInfo()
  } catch (e) { /* 错误已处理 */ }
}

async function toggleChannel(event: string, channel: string, enabled: boolean) {
  try {
    await request.put('/profile/notification-preferences', {
      [event]: { [channel]: enabled },
    })
    ElMessage.success('已更新')
  } catch (e) { /* 错误已处理 */ }
}

async function addRecipient() {
  if (!newRecipient.value.recipient) {
    ElMessage.warning('请输入接收人地址')
    return
  }
  try {
    await request.post('/profile/notification-recipients', newRecipient.value)
    ElMessage.success('已添加')
    newRecipient.value = { channel: 'email', recipient: '', label: '' }
    const res = await request.get('/profile/notification-recipients')
    recipients.value = res.data.items
  } catch (e) { /* 错误已处理 */ }
}

async function toggleRecipient(row: any, enabled: boolean) {
  try {
    await request.put(`/profile/notification-recipients/${row.id}`, { enabled })
    row.enabled = enabled
  } catch (e) { /* 错误已处理 */ }
}

async function removeRecipient(row: any) {
  try {
    await request.delete(`/profile/notification-recipients/${row.id}`)
    ElMessage.success('已删除')
    recipients.value = recipients.value.filter((r: any) => r.id !== row.id)
  } catch (e) { /* 错误已处理 */ }
}

async function saveInfo() {
  try {
    await request.put('/profile/me', form.value)
    ElMessage.success('保存成功')
    userStore.fetchUserInfo()
  } catch (e) { /* 错误已处理 */ }
}

async function changePassword() {
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  try {
    await request.post('/profile/change-password', {
      old_password: pwdForm.value.old_password,
      new_password: pwdForm.value.new_password,
      code: pwdForm.value.code,
    })
    ElMessage.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '', code: '' }
  } catch (e) { /* 错误已处理 */ }
}
</script>
