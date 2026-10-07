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
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><User /></el-icon>
                <div>
                  <div class="sec-title">基本信息</div>
                  <div class="sec-current">完善您的个人资料，生日、性别等信息将展示在个人主页</div>
                </div>
              </div>
              <el-form :model="form" label-width="96px" class="sec-form wide">
                <el-form-item label="用户名">
                  <el-input :model-value="userStore.userInfo?.username" disabled />
                </el-form-item>
                <el-form-item label="姓名">
                  <el-input v-model="form.name" placeholder="请输入姓名" />
                </el-form-item>
                <el-form-item label="生日">
                  <el-date-picker v-model="form.birthday" type="date" value-format="YYYY-MM-DD" class="hj-w-full" />
                </el-form-item>
                <el-form-item label="性别">
                  <el-radio-group v-model="form.gender">
                    <el-radio value="male">男</el-radio>
                    <el-radio value="female">女</el-radio>
                  </el-radio-group>
                </el-form-item>
                <!-- 邮箱/手机号仅展示，换绑请前往「安全设置」标签页 -->
                <el-form-item label="邮箱">
                  <el-input :model-value="userStore.userInfo?.email" placeholder="未绑定" disabled />
                </el-form-item>
                <el-form-item label="手机号">
                  <el-input :model-value="userStore.userInfo?.phone" placeholder="未绑定" disabled />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="saveInfo">保存修改</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="角色权限" name="roles">
          <div class="pane-body">
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Avatar /></el-icon>
                <div>
                  <div class="sec-title">我的角色</div>
                  <div class="sec-current">当前账号拥有的角色，决定您在系统中的操作范围</div>
                </div>
              </div>
              <div class="role-wrap">
                <div v-for="r in roles" :key="r.id" class="role-chip">
                  <el-icon><Avatar /></el-icon>
                  <span>{{ r.role_name }}</span>
                </div>
              </div>
            </div>

            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Key /></el-icon>
                <div>
                  <div class="sec-title">我的权限</div>
                  <div class="sec-current">
                    {{ isSuperAdmin ? '超级管理员，拥有所有权限' : '按功能模块展示当前账号的权限明细' }}
                  </div>
                </div>
              </div>
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
          </div>
        </el-tab-pane>

        <el-tab-pane label="通知偏好" name="notify">
          <div class="pane-body">
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Bell /></el-icon>
                <div>
                  <div class="sec-title">通知偏好</div>
                  <div class="sec-current">选择您希望接收哪些事件的通知，未勾选的渠道将不再推送</div>
                </div>
              </div>
              <el-table :data="preferenceEvents" border class="pref-table">
                <el-table-column prop="name" label="事件" width="220" />
                <el-table-column v-for="ch in channelList" :key="ch.code" :label="ch.name" width="120" align="center">
                  <template #default="{ row }">
                    <el-switch
                      :model-value="(row as PreferenceEvent).channels.find(c => c.code === ch.code)?.enabled"
                      @change="
                        (val: string | number | boolean) =>
                          toggleChannel(row as PreferenceEvent, ch.code, val as boolean)
                      "
                    />
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="第三方账号绑定" name="binding">
          <div class="pane-body">
            <el-alert type="info" :closable="false" class="pane-alert">
              填写钉钉 / 飞书 Webhook
              地址后，通知将按您的偏好推送到对应群聊。标准授权绑定（扫码登录授权、应用内一键绑定）将在后续版本开放。
            </el-alert>

            <!-- 钉钉 -->
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><ChatDotRound /></el-icon>
                <div>
                  <div class="sec-title">钉钉</div>
                  <div class="sec-current">{{ bindingDisplay.dingtalk }}</div>
                </div>
              </div>
              <el-form label-width="130px" class="sec-form">
                <el-form-item label="Webhook 地址">
                  <el-input
                    v-model="bindingForms.dingtalk"
                    placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
                  />
                </el-form-item>
                <el-form-item label="推送启用">
                  <el-switch v-model="bindingEnabled.dingtalk" @change="toggleBinding('dingtalk')" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="saveWebhook('dingtalk')">保存</el-button>
                  <el-button v-if="bindingState.dingtalk" round @click="testWebhook('dingtalk')">测试</el-button>
                  <el-button v-if="bindingState.dingtalk" round @click="unbindWebhook('dingtalk')">解除绑定</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 飞书 -->
            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><Message /></el-icon>
                <div>
                  <div class="sec-title">飞书</div>
                  <div class="sec-current">{{ bindingDisplay.feishu }}</div>
                </div>
              </div>
              <el-form label-width="130px" class="sec-form">
                <el-form-item label="Webhook 地址">
                  <el-input
                    v-model="bindingForms.feishu"
                    placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..."
                  />
                </el-form-item>
                <el-form-item label="推送启用">
                  <el-switch v-model="bindingEnabled.feishu" @change="toggleBinding('feishu')" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round @click="saveWebhook('feishu')">保存</el-button>
                  <el-button v-if="bindingState.feishu" round @click="testWebhook('feishu')">测试</el-button>
                  <el-button v-if="bindingState.feishu" round @click="unbindWebhook('feishu')">解除绑定</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 标准绑定预留（二期 / 三期实质性接入） -->
            <el-alert type="success" :closable="false" class="pane-alert">
              预留能力：后续版本将支持钉钉 / 飞书标准授权绑定（扫码登录授权、应用内一键绑定）， 绑定后无需手动维护
              Webhook 地址，通知将自动推送到您的个人账号。
            </el-alert>
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
                  <div class="sec-title">{{ userStore.userInfo?.phone ? '更换手机号' : '绑定手机' }}</div>
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
                  <div class="sec-title">{{ userStore.userInfo?.email ? '更换邮箱' : '绑定邮箱' }}</div>
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
import { Avatar, Iphone, Message, Lock, ChatDotRound, User, Key, Bell } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  updateMe,
  changePassword,
  sendVerifyCode,
  updatePhone,
  updateEmail,
  getNotificationPreferences,
  updateNotificationPreferences,
  listNotificationRecipients,
  addNotificationRecipient,
  updateNotificationRecipient,
  removeNotificationRecipient,
  testMyRecipient,
  type PreferenceEvent,
} from '@/api/profile'
import type { UserRoleBrief, ProfilePermission } from '@/types/auth'

const userStore = useUserStore()
const activeTab = ref('info')
const roles = ref<UserRoleBrief[]>([])
const permissions = ref<string[]>([])
const permissionList = ref<ProfilePermission[]>([])
const preferenceEvents = ref<PreferenceEvent[]>([])

/** 第三方账号绑定：钉钉 / 飞书 Webhook（作为该渠道推送的默认接收人） */
const bindingState = ref<Record<string, string>>({ dingtalk: '', feishu: '' })
const bindingForms = ref<Record<string, string>>({ dingtalk: '', feishu: '' })
const bindingEnabled = ref<Record<string, boolean>>({ dingtalk: true, feishu: true })

/** 当前已配置 Webhook 的展示文案（脱敏截断） */
const bindingDisplay = computed(() => {
  const display: Record<string, string> = {}
  for (const ch of ['dingtalk', 'feishu'] as const) {
    const url = bindingState.value[ch]
    display[ch] = url ? `已配置：${url.length > 40 ? `${url.slice(0, 40)}…` : url}` : '未配置 Webhook'
  }
  return display
})

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
  await loadBindings()
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

async function toggleChannel(row: PreferenceEvent, channel: string, enabled: boolean) {
  // 乐观更新：先切 UI，再发请求；失败回滚
  const ch = row.channels.find(c => c.code === channel)
  const prev = ch?.enabled
  if (ch) ch.enabled = enabled
  try {
    await updateNotificationPreferences({ [row.event]: { [channel]: enabled } })
    ElMessage.success('已更新')
  } catch {
    if (ch) ch.enabled = prev ?? false
  }
}

/** 加载第三方绑定：读取钉钉 / 飞书渠道已配置的 Webhook 接收人 */
async function loadBindings() {
  try {
    const res = await listNotificationRecipients()
    for (const item of res.data.items) {
      if (item.channel === 'dingtalk' || item.channel === 'feishu') {
        bindingState.value[item.channel] = item.recipient
        bindingForms.value[item.channel] = item.recipient
        bindingEnabled.value[item.channel] = item.enabled
      }
    }
  } catch {
    /* 错误已处理 */
  }
}

/** 保存 Webhook 绑定（新增幂等，重复保存即更新） */
async function saveWebhook(channel: 'dingtalk' | 'feishu') {
  const url = bindingForms.value[channel].trim()
  if (!url) {
    ElMessage.warning('请填写 Webhook 地址')
    return
  }
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    ElMessage.warning('Webhook 地址需以 http:// 或 https:// 开头')
    return
  }
  try {
    await addNotificationRecipient({
      channel,
      recipient: url,
      label: channel === 'dingtalk' ? '钉钉 Webhook' : '飞书 Webhook',
      enabled: bindingEnabled.value[channel],
    })
    bindingState.value[channel] = url
    ElMessage.success('绑定成功')
  } catch {
    /* 错误已处理 */
  }
}

/** 启停推送开关（保留已配置的 Webhook） */
async function toggleBinding(channel: 'dingtalk' | 'feishu') {
  const url = bindingState.value[channel]
  if (!url) {
    // 无已存 Webhook 时仅记录开关状态，等待用户填写后保存
    return
  }
  try {
    await updateNotificationRecipient({
      channel,
      recipient: url,
      enabled: bindingEnabled.value[channel],
    })
    ElMessage.success(bindingEnabled.value[channel] ? '已启用推送' : '已停用推送')
  } catch {
    /* 错误已处理 */
  }
}

/** 解除绑定：删除该渠道 Webhook 接收人 */
async function unbindWebhook(channel: 'dingtalk' | 'feishu') {
  const url = bindingState.value[channel]
  if (!url) return
  try {
    await removeNotificationRecipient(channel, url)
    bindingState.value[channel] = ''
    bindingForms.value[channel] = ''
    bindingEnabled.value[channel] = true
    ElMessage.success('已解除绑定')
  } catch {
    /* 错误已处理 */
  }
}

/** 测试我的 Webhook 连通性 */
async function testWebhook(channel: 'dingtalk' | 'feishu') {
  if (!bindingState.value[channel]) return
  try {
    const res = await testMyRecipient(channel)
    if (res.data.success) {
      ElMessage.success('测试消息已发送，请查收')
    } else {
      ElMessage.error(res.data.error || '发送失败')
    }
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
  width: 100%;
  padding: 8px 0 24px;
}

/* ===== 顶部信息横幅（参考开放平台：紧凑、左对齐） ===== */
.hero-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 20px 24px;
  border-radius: 12px;
  color: #303133;
  background: #fff;
  border: 1px solid #eef0f4;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.05);
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.hero-avatar {
  background: #79bbff;
  color: #fff;
  font-size: 26px;
  font-weight: 600;
  border: none;
  flex-shrink: 0;
}

.hero-name {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.hero-sub {
  margin-top: 3px;
  font-size: 13px;
  color: #909399;
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.hero-tag {
  padding: 2px 10px;
  font-size: 12px;
  border-radius: 999px;
  border: 1px solid #e4e8f2;
  background: #ecf5ff;
  color: #409eff;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 18px;
  border-radius: 10px;
  background: #f7f9fc;
  border: 1px solid #eef0f4;
}

.stat-item {
  text-align: center;
  min-width: 56px;
}

.stat-num {
  font-size: 17px;
  font-weight: 600;
}

.stat-label {
  margin-top: 3px;
  font-size: 12px;
  color: #909399;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: #e0e6ef;
}

/* ===== 主体卡片 ===== */
.main-card {
  margin-top: 16px;
  border-radius: 12px;
  border: 1px solid #eef0f4;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.05);
}

.profile-tabs :deep(.el-tabs__header) {
  padding: 0 20px;
  margin-bottom: 0;
}

.profile-tabs :deep(.el-tabs__nav-wrap) {
  padding-top: 6px;
}

.pane-body {
  padding: 20px 24px 28px;
}

.pane-alert {
  margin-bottom: 20px;
  border-radius: 10px;
}

/* 基本信息表单：卡片内占满宽度（覆盖 sec-form 默认 420px 限制） */
.sec-form.wide {
  width: 100%;
  max-width: 560px;
}

/* ===== 角色权限 ===== */
.role-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
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
  border: 1px solid #eef0f4;
  border-radius: 12px; /* 与 hero-card / main-card 圆角一致 */
  padding: 22px 24px;
  margin-bottom: 18px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.05); /* 与页面卡片阴影一致 */
  transition: box-shadow 0.2s ease;
}

.sec-card:hover {
  box-shadow: 0 4px 16px rgba(31, 45, 61, 0.08);
}

.sec-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 14px;
  margin-bottom: 16px;
  border-bottom: 1px solid #f0f2f5; /* 标题区与表单分区 */
}

.sec-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #66b1ff); /* 品牌蓝渐变 */
  color: #fff;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.28);
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
  width: 420px;
  max-width: 100%;
}

/* 表单项间距收紧，表单更精致 */
.sec-form .el-form-item {
  margin-bottom: 14px;
}
.sec-form .el-form-item:last-child {
  margin-bottom: 0;
}
.sec-form .el-form-item__label {
  color: #606266;
}

/* 输入框/按钮圆角统一，视觉更柔和 */
.sec-form .el-input__wrapper {
  border-radius: 8px;
}
.sec-form .el-button {
  border-radius: 8px;
}

/* 验证码行：按钮不压缩、不换行 */
.code-row .el-button {
  flex-shrink: 0;
  min-width: 92px;
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
