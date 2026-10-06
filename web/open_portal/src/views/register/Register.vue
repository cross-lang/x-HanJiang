<template>
  <div class="register-container">
    <el-card class="register-card" shadow="never" body-style="padding:0">
      <div class="register-inner">
        <!-- 左侧品牌区 -->
        <div class="register-left">
          <img src="/logo-icon.png" class="register-logo" alt="汉江开放平台" />
          <h1 class="brand-name">汉江开放平台</h1>
          <p class="brand-sub">HanJiang Open Platform</p>
          <p class="brand-desc">注册成为开发者，创建应用并申请开放能力</p>
        </div>

        <!-- 右侧注册表单 -->
        <div class="register-right">
          <h2 class="register-title">注册开发者账号</h2>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="0" class="register-form">
            <el-form-item prop="name">
              <el-input
                v-model="form.name"
                placeholder="昵称（1-100 位）"
                prefix-icon="Avatar"
                size="large"
                class="big-input"
              />
            </el-form-item>
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名（3-50 位）"
                prefix-icon="User"
                size="large"
                class="big-input"
              />
            </el-form-item>
            <el-form-item prop="email">
              <el-input
                v-model="form.email"
                placeholder="邮箱（用于接收通知与验证）"
                prefix-icon="Message"
                size="large"
                class="big-input"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码（至少 8 位）"
                prefix-icon="Lock"
                show-password
                size="large"
                class="big-input"
              />
            </el-form-item>
            <el-form-item prop="confirm_password">
              <el-input
                v-model="form.confirm_password"
                type="password"
                placeholder="确认密码"
                prefix-icon="Lock"
                show-password
                size="large"
                class="big-input"
                @keyup.enter="handleRegister"
              />
            </el-form-item>

            <!-- 认证主体类型（预留：后续认证流程启用） -->
            <el-form-item prop="certification_type">
              <el-radio-group v-model="form.certification_type">
                <el-radio value="personal">个人开发者</el-radio>
                <el-radio value="enterprise">企业开发者</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-button
              type="primary"
              class="register-btn"
              size="large"
              :loading="loading"
              @click="handleRegister"
            >
              注 册
            </el-button>
          </el-form>

          <div class="login-row">
            已有账号？<router-link to="/login" class="login-link">直接登录</router-link>
          </div>
        </div>
      </div>
    </el-card>

    <footer class="register-footer">Copyright © 2026 汉江开放平台 All Rights Reserved</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { register } from '@/api/auth'

const router = useRouter()

const formRef = ref<FormInstance>()
const form = ref<{
  name: string
  username: string
  email: string
  password: string
  confirm_password: string
  certification_type: 'personal' | 'enterprise'
}>({
  name: '',
  username: '',
  email: '',
  password: '',
  confirm_password: '',
  certification_type: 'personal',
})
const loading = ref(false)

const rules: FormRules = {
  name: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { min: 1, max: 100, message: '昵称长度为 1-100 位', trigger: 'blur' },
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为 3-50 位', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8-64 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.value.password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
  certification_type: [
    { required: true, message: '请选择认证主体类型', trigger: 'change' },
  ],
}

async function handleRegister() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await register(form.value)
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef5ff 0%, #f5f7fa 100%);
}

.register-card {
  width: 880px;
  max-width: 94vw;
  border-radius: 16px;
  border: none;
  box-shadow: 0 12px 40px rgba(31, 45, 61, 0.12);
  overflow: hidden;
}
.register-inner {
  display: flex;
  min-height: 560px;
}
.register-left {
  flex: 0 0 38%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
  background:
    radial-gradient(120% 120% at 15% 10%, rgba(255, 255, 255, 0.16) 0%, transparent 55%),
    linear-gradient(160deg, #409eff 0%, #2b7de0 55%, #1f63c9 100%);
  color: #fff;
  overflow: hidden;
}
.register-left::before,
.register-left::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
}
.register-left::before {
  width: 260px;
  height: 260px;
  right: -90px;
  top: -80px;
}
.register-left::after {
  width: 180px;
  height: 180px;
  left: -60px;
  bottom: -60px;
}
.register-logo {
  width: 92px;
  height: 92px;
  border-radius: 22px;
  display: block;
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  position: relative;
  z-index: 1;
}
.brand-name {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 1px;
  position: relative;
  z-index: 1;
}
.brand-sub {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.5px;
  position: relative;
  z-index: 1;
}
.brand-desc {
  margin-top: 20px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  text-align: center;
  padding: 0 24px;
  position: relative;
  z-index: 1;
}
.register-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 36px 48px;
  background: var(--hj-bg-card);
}
.register-title {
  margin: 0 0 24px;
  font-size: 22px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.register-form .el-form-item {
  margin-bottom: 16px;
}
.big-input :deep(.el-input__inner) {
  font-size: 15px;
  height: 44px;
}

.register-btn.el-button--primary {
  width: 100%;
  margin-top: 8px;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #2b7de0);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.register-btn.el-button--primary:hover {
  background: linear-gradient(135deg, #66b1ff, #409eff);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.36);
}
.register-btn.el-button--primary:active {
  transform: translateY(1px);
}

.login-row {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: var(--hj-text-secondary);
}
.login-link {
  color: var(--hj-primary);
  text-decoration: none;
  font-weight: 500;
}

@media (max-width: 760px) {
  .register-left {
    display: none;
  }
  .register-right {
    padding: 32px 28px;
  }
}

.register-footer {
  position: fixed;
  bottom: 18px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 13px;
  color: var(--hj-text-regular);
  letter-spacing: 0.3px;
}
</style>
