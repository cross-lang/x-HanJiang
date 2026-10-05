<template>
  <div class="profile-page">
    <!-- 顶部信息横幅 -->
    <div class="hero-card">
      <div class="hero-left">
        <el-avatar :size="80" class="hero-avatar">{{ initial }}</el-avatar>
        <div class="hero-info">
          <div class="hero-name">{{ developerStore.profile?.name || developerStore.profile?.username }}</div>
          <div class="hero-sub">@{{ developerStore.profile?.username }}</div>
          <div class="hero-tags">
            <el-tag v-if="developerStore.profile?.certification_type === 'enterprise'" type="warning" size="small">
              企业开发者
            </el-tag>
            <el-tag v-else-if="developerStore.profile?.certification_type === 'personal'" type="success" size="small">
              个人开发者
            </el-tag>
            <el-tag v-else type="info" size="small">未认证</el-tag>
          </div>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <div class="stat-num">{{ certificationStatusText }}</div>
          <div class="stat-label">认证状态</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ developerStore.profile?.email ? '已绑定' : '未绑定' }}</div>
          <div class="stat-label">邮箱</div>
        </div>
        <div class="stat-divider" />
        <div class="stat-item">
          <div class="stat-num">{{ developerStore.profile?.phone ? '已绑定' : '未绑定' }}</div>
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
                <el-input :model-value="developerStore.profile?.username" disabled />
              </el-form-item>
              <el-form-item label="昵称">
                <el-input v-model="form.name" placeholder="请输入昵称" />
              </el-form-item>
              <el-form-item label="手机号">
                <el-input v-model="form.phone" placeholder="请输入手机号" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input :model-value="developerStore.profile?.email" placeholder="未绑定" disabled />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" round @click="saveInfo">保存修改</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="安全设置" name="security">
          <div class="pane-body">
            <el-alert type="info" :closable="false" class="pane-alert">
              修改密码需提供原密码验证。手机号/邮箱换绑（验证码二次认证）为规划中的安全能力，后续开放。
            </el-alert>

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
                  <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码（至少 8 位）" />
                </el-form-item>
                <el-form-item label="确认密码">
                  <el-input
                    v-model="pwdForm.confirm_password"
                    type="password"
                    show-password
                    placeholder="请再次输入新密码"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round :loading="pwdLoading" @click="changePwd">修改密码</el-button>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="开发者认证" name="certification">
          <div class="pane-body">
            <el-alert type="info" :closable="false" class="pane-alert">
              开发者认证为预留能力：选择个人认证或企业认证后提交申请，管理员审批通过后可解锁更高调用配额与专属权益。
            </el-alert>

            <div class="sec-card">
              <div class="sec-header">
                <el-icon class="sec-icon"><User /></el-icon>
                <div>
                  <div class="sec-title">认证申请</div>
                  <div class="sec-current">当前状态：{{ certificationStatusText }}</div>
                </div>
              </div>
              <el-form :model="certForm" label-width="88px" class="sec-form">
                <el-form-item label="认证类型">
                  <el-radio-group v-model="certForm.certification_type" :disabled="certificationSubmitted">
                    <el-radio value="personal">个人认证</el-radio>
                    <el-radio value="enterprise">企业认证</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item v-if="certForm.certification_type === 'enterprise'" label="企业名称">
                  <el-input v-model="certForm.company_name" placeholder="请输入营业执照上的企业名称" :disabled="certificationSubmitted" />
                </el-form-item>
                <el-form-item v-if="certForm.certification_type === 'enterprise'" label="信用代码">
                  <el-input v-model="certForm.credential_no" placeholder="统一社会信用代码" :disabled="certificationSubmitted" />
                </el-form-item>
                <el-form-item label="身份证号" v-if="certForm.certification_type === 'personal'">
                  <el-input v-model="certForm.credential_no" placeholder="个人实名信息（预留）" :disabled="certificationSubmitted" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" round :loading="certLoading" :disabled="certificationSubmitted" @click="submitCertification">
                    {{ certificationSubmitted ? '已提交，等待审批' : '提交认证申请' }}
                  </el-button>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useDeveloperStore } from '@/stores/developer'
import { updateDeveloperProfile, applyCertification } from '@/api/developer'
import { changePassword } from '@/api/auth'

const developerStore = useDeveloperStore()
const activeTab = ref('info')

const initial = computed(() => (developerStore.profile?.name || 'D').charAt(0))

const CERT_TEXTS: Record<string, string> = {
  none: '未认证',
  pending: '审批中',
  approved: '已认证',
  rejected: '已驳回',
}
const certificationStatusText = computed(
  () => CERT_TEXTS[developerStore.profile?.certification_status || 'none'] || '未认证',
)
const certificationSubmitted = computed(() => developerStore.profile?.certification_status === 'pending')

const form = ref({ name: '', phone: '' })
const pwdForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const pwdLoading = ref(false)

const certForm = ref<{
  certification_type: 'personal' | 'enterprise'
  company_name: string
  credential_no: string
}>({ certification_type: 'personal', company_name: '', credential_no: '' })
const certLoading = ref(false)

onMounted(async () => {
  const info = await developerStore.fetchProfile()
  if (info) {
    form.value = { name: info.name || '', phone: info.phone || '' }
    certForm.value.certification_type = info.certification_type || 'personal'
    certForm.value.company_name = info.company_name || ''
  }
})

async function saveInfo() {
  try {
    await updateDeveloperProfile(form.value)
    ElMessage.success('保存成功')
    developerStore.fetchProfile()
  } catch {
    // 错误已处理
  }
}

async function changePwd() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    ElMessage.warning('请填写原密码与新密码')
    return
  }
  if (pwdForm.value.new_password !== pwdForm.value.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await changePassword(pwdForm.value)
    ElMessage.success('密码修改成功，请重新登录')
    developerStore.logout()
    window.location.href = '/login'
  } catch {
    // 错误已处理
  } finally {
    pwdLoading.value = false
  }
}

async function submitCertification() {
  if (certForm.value.certification_type === 'enterprise' && !certForm.value.company_name.trim()) {
    ElMessage.warning('请输入企业名称')
    return
  }
  certLoading.value = true
  try {
    await applyCertification({
      certification_type: certForm.value.certification_type,
      company_name: certForm.value.company_name.trim() || undefined,
      credential_no: certForm.value.credential_no.trim() || undefined,
    })
    ElMessage.success('认证申请已提交，等待管理员审批')
    developerStore.fetchProfile()
  } catch {
    // 错误已处理
  } finally {
    certLoading.value = false
  }
}
</script>

<style scoped>
.profile-page {
  /* 全宽铺满内容区，减少无用的空白 */
  padding: 8px 4px 24px;
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
  background:
    radial-gradient(90% 140% at 100% 0%, rgba(64, 158, 255, 0.08) 0%, transparent 55%),
    var(--hj-bg-card);
  border: 1px solid var(--hj-border-lighter);
  box-shadow: var(--hj-shadow-card);
}
.hero-left {
  display: flex;
  align-items: center;
  gap: 20px;
}
.hero-avatar {
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  color: #fff;
  font-size: 32px;
  font-weight: 600;
  border: none;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}
.hero-name {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.hero-sub {
  margin-top: 4px;
  font-size: 14px;
  color: var(--hj-text-secondary);
}
.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.hero-stats {
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 26px;
  border-radius: 12px;
  background: var(--hj-bg-page);
  border: 1px solid var(--hj-border-lighter);
}
.stat-item {
  text-align: center;
  min-width: 64px;
}
.stat-num {
  font-size: 17px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.stat-label {
  margin-top: 3px;
  font-size: 12px;
  color: #909399;
}
.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--hj-border);
}

/* ===== 主体卡片 ===== */
.main-card {
  margin-top: 20px;
  border-radius: 16px;
  border: 1px solid var(--hj-border-lighter);
  box-shadow: var(--hj-shadow-card);
}
.profile-tabs :deep(.el-tabs__header) {
  padding: 0 24px;
  margin-bottom: 0;
}
.profile-tabs :deep(.el-tabs__item) {
  font-size: 14px;
  font-weight: 500;
  height: 48px;
  line-height: 48px;
}
.profile-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
}
.profile-tabs :deep(.el-tabs__active-bar) {
  height: 3px;
  border-radius: 2px;
}
.pane-body {
  padding: 28px 32px 36px;
}
.pane-alert {
  margin-bottom: 20px;
  border-radius: 10px;
}
.info-form {
  max-width: 520px;
}

/* ===== 安全设置 / 认证 ===== */
.sec-card {
  border: 1px solid var(--hj-border-light);
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 18px;
  background: var(--hj-bg-card);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.sec-card:hover {
  border-color: var(--hj-primary-border);
  box-shadow: var(--hj-shadow-card);
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
  background: linear-gradient(135deg, var(--hj-primary-bg), #f5faff);
  color: var(--hj-primary);
  font-size: 20px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sec-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.sec-current {
  margin-top: 2px;
  font-size: 12px;
  color: var(--hj-text-secondary);
}
.sec-form {
  max-width: 520px;
}
</style>
