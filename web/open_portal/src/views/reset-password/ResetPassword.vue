<template>
  <div class="reset-container">
    <el-card class="reset-card" shadow="never" body-style="padding:0">
      <div class="reset-inner">
        <!-- 左侧品牌区 -->
        <div class="reset-left">
          <img src="/logo-icon.png" class="reset-logo" alt="汉江开放平台" />
          <h1 class="brand-name">汉江开放平台</h1>
          <p class="brand-sub">HanJiang Open Platform</p>
          <p class="brand-desc">设置新密码，重新开启你的开发之旅</p>
        </div>

        <!-- 右侧表单 -->
        <div class="reset-right">
          <h2 class="reset-title">重置密码</h2>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="0" class="reset-form">
            <el-form-item prop="new_password">
              <el-input
                v-model="form.new_password"
                type="password"
                placeholder="新密码（至少 8 位）"
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
                placeholder="确认新密码"
                prefix-icon="Lock"
                show-password
                size="large"
                class="big-input"
                @keyup.enter="handleSubmit"
              />
            </el-form-item>

            <el-button
              type="primary"
              class="reset-btn"
              size="large"
              :loading="loading"
              @click="handleSubmit"
            >
              重置密码
            </el-button>
          </el-form>

          <div class="back-row">
            <router-link to="/login" class="back-link">← 返回登录</router-link>
          </div>
        </div>
      </div>
    </el-card>

    <footer class="reset-footer">Copyright © 2026 汉江开放平台 All Rights Reserved</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { resetPassword } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const form = ref({ new_password: '', confirm_password: '' })
const loading = ref(false)

const rules: FormRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8-64 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.value.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function handleSubmit() {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    ElMessage.error('缺少重置令牌，请从邮件中的链接进入')
    return
  }
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await resetPassword({ token, ...form.value })
    ElMessage.success('密码重置成功，请使用新密码登录')
    router.push('/login')
  } catch {
    // 错误已处理（令牌无效/过期等）
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef5ff 0%, #f5f7fa 100%);
}

.reset-card {
  width: 860px;
  max-width: 94vw;
  border-radius: 16px;
  border: none;
  box-shadow: 0 12px 40px rgba(31, 45, 61, 0.12);
  overflow: hidden;
}
.reset-inner {
  display: flex;
  min-height: 480px;
}
.reset-left {
  flex: 0 0 42%;
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
.reset-left::before,
.reset-left::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
}
.reset-left::before {
  width: 260px;
  height: 260px;
  right: -90px;
  top: -80px;
}
.reset-left::after {
  width: 180px;
  height: 180px;
  left: -60px;
  bottom: -60px;
}
.reset-logo {
  width: 96px;
  height: 96px;
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
  margin-top: 22px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  position: relative;
  z-index: 1;
}
.reset-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 56px;
  background: var(--hj-bg-card);
}
.reset-title {
  margin: 0 0 28px;
  font-size: 22px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.reset-form .el-form-item {
  margin-bottom: 22px;
}
.big-input :deep(.el-input__inner) {
  font-size: 15px;
  height: 48px;
}

.reset-btn.el-button--primary {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #2b7de0);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.reset-btn.el-button--primary:hover {
  background: linear-gradient(135deg, #66b1ff, #409eff);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.36);
}
.reset-btn.el-button--primary:active {
  transform: translateY(1px);
}

.back-row {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
}
.back-link {
  color: var(--hj-primary);
  text-decoration: none;
  font-weight: 500;
}
.back-link:hover {
  color: #66b1ff;
}

@media (max-width: 760px) {
  .reset-left {
    display: none;
  }
  .reset-right {
    padding: 40px 32px;
  }
}

.reset-footer {
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
