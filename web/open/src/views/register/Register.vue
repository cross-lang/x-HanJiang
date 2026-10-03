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
  username: string
  email: string
  password: string
  confirm_password: string
  certification_type: 'personal' | 'enterprise'
}>({
  username: '',
  email: '',
  password: '',
  confirm_password: '',
  certification_type: 'personal',
})
const loading = ref(false)

const rules: FormRules = {
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
  width: 860px;
  max-width: 94vw;
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
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
  background: #fff;
  border-right: 1px solid #f0f0f0;
}
.register-logo {
  width: 100px;
  height: 100px;
  border-radius: 20px;
  display: block;
  margin-bottom: 16px;
}
.brand-name {
  font-size: 26px;
  font-weight: 600;
  color: #409eff;
  margin: 0;
}
.brand-sub {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}
.brand-desc {
  margin-top: 20px;
  font-size: 13px;
  color: #c0c4cc;
  text-align: center;
  padding: 0 24px;
}
.register-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 36px 48px;
  background: #fff;
}
.register-title {
  margin: 0 0 24px;
  font-size: 22px;
  font-weight: 500;
  color: #303133;
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
  letter-spacing: 4px;
  border-radius: 6px;
  background: #409eff;
  border: none;
}
.register-btn.el-button--primary:hover {
  background: #66b1ff;
}

.login-row {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  color: #909399;
}
.login-link {
  color: #409eff;
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
  color: #606266;
  user-select: none;
}
</style>
