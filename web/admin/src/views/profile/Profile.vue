<template>
  <div class="profile-page">
    <!-- 顶部信息横幅 -->
    <div class="hero-card">
      <div class="hero-left">
        <el-avatar :size="80" class="hero-avatar">{{ initial }}</el-avatar>
        <div class="hero-info">
          <div class="hero-name">{{ userStore.userInfo?.name || userStore.userInfo?.username }}</div>
          <div class="hero-sub">@{{ userStore.userInfo?.username }}</div>
          <div class="hero-tags">
            <span v-for="r in roles" :key="r.id" class="hero-tag">{{ r.role_name }}</span>
          </div>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <div class="stat-num">{{ roles.length }}</div>
          <div class="stat-label">角色</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ isSuperAdmin ? '∞' : permissionList.length }}</div>
          <div class="stat-label">权限</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ userStore.userInfo?.email ? '已绑定' : '未绑定' }}</div>
          <div class="stat-label">邮箱</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ userStore.userInfo?.phone ? '已绑定' : '未绑定' }}</div>
          <div class="stat-label">手机</div>
        </div>
      </div>
    </div>

    <!-- 主体卡片 -->
    <el-card class="main-card" shadow="never">
      <el-tabs v-model="activeTab" class="profile-tabs">
        <el-tab-pane label="基本信息" name="info">
          <div class="pane-body">
            <el-form :model="form" label-width="96px" class="info-form">
              <el-form-item label="用户名">
                <el-input :model-value="userStore.userInfo?.username" disabled />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="form.name" placeholder="请输入姓名" />
              </el-form-item>
              <el-form-item label="生日">
                <el-date-picker v-model="form.birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
              <el-form-item label="性别">
                <el-radio-group v-model="form.gender">
                  <el-radio value="male">男</el-radio>
                  <el-radio value="female">女</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" round @click="saveInfo">保存修改</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="角色权限" name="roles">
          <div class="pane-body">
            <h4 class="pane-title">我的角色</h4>
            <div class="role-wrap">
              <div v-for="r in roles" :key="r.id" class="role-chip">
                <el-icon><Avatar /></el-icon>
                <span>{{ r.role_name }}</span>
              </div>
            </div>

            <h4 class="pane-title">我的权限</h4>
            <el-alert v-if="isSuperAdmin" type="success" :closable="false" class="pane-alert">
              超级管理员，拥有所有权限
            </el-alert>
            <div v-else class="perm-grid">
              <div v-for="group in groupedPermissions" :key="group.module" class="perm-card">
                <div class="perm-module">{{ group.module_label || group.module }}</div>
                <div v-for="p in group.items" :key="p.code" class="perm-item">
                  <span>{{ p.name }}</span>
                  <span class="perm-code">{{ p.code }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="通知偏好" name="notify">
          <div class="pane-body">
            <el-alert type="info" :closable="false" class="pane-alert">
              选择您希望接收哪些事件的通知，未勾选的将不再推送
            </el-alert>
            <el-table :data="preferenceEvents" border class="pref-table">
              <el-table-column prop="name" label="事件" width="220" />
              <el-table-column v-for="ch in channelList" :key="ch.code" :label="ch.name" width="120" align="center">
                <template #default="{ row }">
                  <el-switch
                    :model-value="(row as PreferenceEvent).channels.find(c => c.code === ch.code)?.enabled"
                    @change="(val: string | number | boolean) => toggleChannel(row.event, ch.code, val as boolean)"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="安全设置" name="security">
          <div class="pane-body">
            <el-alert type="warning" :closable="false" class="pane-alert">
              修改手机号、邮箱、密码均需通过验证码二次认证
            </el-alert>

            <!-- 手机 -->
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Iphone /></el-icon>
                <div>
                  <div class="sec-title">绑定手机</div>
                  <div class="sec-current">当前：{{ userStore.userInfo?.phone || '未绑定' }}</div>
                </div>
              </div>
              <el-form :model="phoneForm" label-width="88px" class="sec-form">
                <el-form-item label="新手机号">
                  <el-input v-model="phoneForm.phone" placeholder="请输入新手机号" />
                </el-form-item>
                <el-form-item label="验证码">
                  <div class="code-row">
                    <el-input v-model="phoneForm.code" placeholder="6 位验证码" />
                    <el-button @click="sendCode" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="updatePhoneInfo">修改手机号</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 邮箱 -->
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Message /></el-icon>
                <div>
                  <div class="sec-title">绑定邮箱</div>
                  <div class="sec-current">当前：{{ userStore.userInfo?.email || '未绑定' }}</div>
                </div>
              </div>
              <el-form :model="emailForm" label-width="88px" class="sec-form">
                <el-form-item label="新邮箱">
                  <el-input v-model="emailForm.email" placeholder="请输入新邮箱" />
                </el-form-item>
                <el-form-item label="验证码">
                  <div class="code-row">
                    <el-input v-model="emailForm.code" placeholder="6 位验证码" />
                    <el-button @click="sendCode" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="updateEmailInfo">修改邮箱</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 密码 -->
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Lock /></el-icon>
                <div>
                  <div class="sec-title">修改密码</div>
                  <div class="sec-current">定期更换密码有助于提升账号安全性</div>
                </div>
              </div>
              <el-form :model="pwdForm" label-width="88px" class="sec-form">
                <el-form-item label="原密码">
                  <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入原密码" />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码" />
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input
                    v-model="pwdForm.confirm_password"
                    type="password"
                    show-password
                    placeholder="请再次输入新密码"
                  />
                </el-form-item>
                <el-form-item label="验证码">
                  <div class="code-row">
                    <el-input v-model="pwdForm.code" placeholder="6 位验证码" />
                    <el-button @click="sendCode" :loading="codeLoading">发送验证码</el-button>
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="changePwd">修改密码</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Avatar, Iphone, Message, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  updateMe,
  changePassword,
  sendVerifyCode,
  updatePhone,
  updateEmail,
  getNotificationPreferences,
  updateNotificationPreferences,
  type PreferenceEvent,
} from '@/api/profile'
import type { UserRoleBrief, ProfilePermission } from '@/types/auth'

const userStore = useUserStore()
const activeTab = ref('info')
const roles = ref<UserRoleBrief[]>([])
const permissions = ref<string[]>([])
const permissionList = ref<ProfilePermission[]>([])
const preferenceEvents = ref<PreferenceEvent[]>([])

const channelList = [
  { code: 'station', name: '站内信' },
  { code: 'email', name: '邮件' },
  { code: 'dingtalk', name: '钉钉' },
  { code: 'feishu', name: '飞书' },
]

const initial = computed(() => (userStore.userInfo?.name || 'U').charAt(0))
const isSuperAdmin = computed(() => permissions.value.includes('*'))

const groupedPermissions = computed(() => {
  const map: Record<string, ProfilePermission[]> = {}
  for (const p of permissionList.value) {
    if (!map[p.module]) map[p.module] = []
    map[p.module].push(p)
  }
  return Object.entries(map).map(([module, items]) => ({
    module,
    module_label: items[0]?.module_label || module,
    items,
  }))
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
    const res = await getNotificationPreferences()
    preferenceEvents.value = res.data.events
  } catch {
    /* ignore */
  }
})

async function sendCode() {
  codeLoading.value = true
  try {
    await sendVerifyCode()
    ElMessage.success('验证码已发送至邮箱，5 分钟内有效')
  } catch {
    // 错误已处理
  } finally {
    codeLoading.value = false
  }
}

async function updatePhoneInfo() {
  if (!phoneForm.value.phone) {
    ElMessage.warning('请输入新手机号')
    return
  }
  try {
    await updatePhone(phoneForm.value.phone, phoneForm.value.code)
    ElMessage.success('手机号修改成功')
    phoneForm.value = { phone: '', code: '' }
    userStore.fetchUserInfo()
  } catch {
    /* 错误已处理 */
  }
}

async function updateEmailInfo() {
  if (!emailForm.value.email) {
    ElMessage.warning('请输入新邮箱')
    return
  }
  try {
    await updateEmail(emailForm.value.email, emailForm.value.code)
    ElMessage.success('邮箱修改成功')
    emailForm.value = { email: '', code: '' }
    userStore.fetchUserInfo()
  } catch {
    /* 错误已处理 */
  }
}

async function toggleChannel(event: string, channel: string, enabled: boolean) {
  try {
    await updateNotificationPreferences({ [event]: { [channel]: enabled } })
    ElMessage.success('已更新')
  } catch {
    /* 错误已处理 */
  }
}

async function saveInfo() {
  try {
    await updateMe(form.value)
    ElMessage.success('保存成功')
    userStore.fetchUserInfo()
  } catch {
    /* 错误已处理 */
  }
}

async function changePwd() {
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  try {
    await changePassword(pwdForm.value.old_password, pwdForm.value.new_password, pwdForm.value.code)
    ElMessage.success('密码修改成功')
    pwdForm.value = { old_password: '', new_password: '', confirm_password: '', code: '' }
  } catch {
    /* 错误已处理 */
  }
}
</script>
<style scoped>
.profile-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 8px 0 24px;
}

/* ===== 顶部信息横幅 ===== */
.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  padding: 28px 32px;
  border-radius: 16px;
  color: #303133;
  background: #fff;
  border: 1px solid #eef0f4;
  box-shadow: 0 4px 16px rgba(31, 45, 61, 0.06);
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.hero-avatar {
  background: #79bbff;
  color: #fff;
  font-size: 32px;
  font-weight: 600;
  border: none;
  flex-shrink: 0;
}

.hero-name {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.hero-sub {
  margin-top: 4px;
  font-size: 14px;
  color: #909399;
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.hero-tag {
  padding: 3px 12px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid #e4e8f2;
  background: #ecf5ff;
  color: #409eff;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 26px;
  border-radius: 12px;
  background: #f7f9fc;
  border: 1px solid #eef0f4;
}

.stat-item {
  text-align: center;
  min-width: 64px;
}

.stat-num {
  font-size: 20px;
  font-weight: 600;
}

.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: #e0e6ef;
}

/* ===== 主体卡片 ===== */
.main-card {
  margin-top: 20px;
  border-radius: 16px;
  border: 1px solid #eef0f4;
  box-shadow: 0 4px 16px rgba(31, 45, 61, 0.06);
}

.profile-tabs :deep(.el-tabs__header) {
  padding: 0 24px;
  margin-bottom: 0;
}

.profile-tabs :deep(.el-tabs__nav-wrap) {
  padding-top: 6px;
}

.pane-body {
  padding: 28px 32px 36px;
}

.pane-title {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.pane-alert {
  margin-bottom: 20px;
  border-radius: 10px;
}

.info-form {
  max-width: 520px;
}

/* ===== 角色权限 ===== */
.role-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 34px;
}

.role-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border-radius: 999px;
  background: linear-gradient(135deg, #ecf5ff 0%, #d9ecff 100%);
  color: #409eff;
  font-size: 14px;
  font-weight: 500;
}

.perm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.perm-card {
  border: 1px solid #eceef3;
  border-radius: 12px;
  padding: 18px 20px;
  background: #fafbfd;
  transition: box-shadow 0.2s ease;
}

.perm-card:hover {
  box-shadow: 0 4px 12px rgba(31, 45, 61, 0.08);
}

.perm-module {
  font-weight: 600;
  color: #409eff;
  margin-bottom: 12px;
  font-size: 14px;
}

.perm-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
  color: #555;
}

.perm-code {
  color: #a0a6b1;
  font-size: 12px;
}

/* ===== 通知偏好 ===== */
.pref-table {
  border-radius: 10px;
  overflow: hidden;
}

/* ===== 安全设置 ===== */
.sec-card {
  border: 1px solid #eceef3;
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 18px;
  background: #fff;
  transition: box-shadow 0.2s ease;
}

.sec-card:hover {
  box-shadow: 0 4px 14px rgba(31, 45, 61, 0.07);
}

.sec-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.sec-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #ecf5ff;
  color: #409eff;
  font-size: 20px;
  flex-shrink: 0;
}

.sec-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.sec-current {
  margin-top: 2px;
  font-size: 12px;
  color: #909399;
}

.sec-form {
  max-width: 520px;
}

.code-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.code-row .el-input {
  flex: 1;
}
</style>
