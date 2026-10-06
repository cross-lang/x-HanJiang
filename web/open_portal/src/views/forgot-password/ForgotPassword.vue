<template>
  <div class="forgot-container">
    <el-card class="forgot-card" shadow="never" body-style="padding:0">
      <div class="forgot-inner">
        <!-- 左侧品牌区 -->
        <div class="forgot-left">
          <img src="/logo-icon.png" class="forgot-logo" alt="汉江开放平台" />
          <h1 class="brand-name">汉江开放平台</h1>
          <p class="brand-sub">HanJiang Open Platform</p>
          <p class="brand-desc">忘记密码？通过注册邮箱完成身份验证</p>
        </div>

        <!-- 右侧表单 -->
        <div class="forgot-right">
          <h2 class="forgot-title">找回密码</h2>

          <el-form ref="formRef" :model="form" :rules="rules" label-width="0" class="forgot-form">
            <el-form-item prop="email">
              <el-input
                v-model="form.email"
                placeholder="请输入注册邮箱"
                prefix-icon="Message"
                size="large"
                class="big-input"
                @keyup.enter="handleSubmit"
              />
            </el-form-item>

            <el-button
              type="primary"
              class="forgot-btn"
              size="large"
              :loading="loading"
              @click="handleSubmit"
            >
              发送重置邮件
            </el-button>
          </el-form>

          <div class="tip-text">
            提交后系统将向该邮箱发送一封含重置链接的邮件，<b>链接 30 分钟内有效</b>，且仅可使用一次。
          </div>

          <div class="back-row">
            <router-link to="/login" class="back-link">← 返回登录</router-link>
          </div>
        </div>
      </div>
    </el-card>

    <footer class="forgot-footer">Copyright © 2026 汉江开放平台 All Rights Reserved</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { forgotPassword } from '@/api/auth'

const router = useRouter()

const formRef = ref<FormInstance>()
const form = ref({ email: '' })
const loading = ref(false)

const rules: FormRules = {
  email: [
    { required: true, message: '请输入注册邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    await forgotPassword(form.value)
    // 无论邮箱是否注册均返回成功提示（避免账号枚举）
    ElMessage.success('重置链接已发送，请前往邮箱查收（30 分钟内有效）')
    router.push('/login')
  } catch {
    // 错误已处理（邮件发送失败等）
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.forgot-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #eef5ff 0%, #f5f7fa 100%);
}

.forgot-card {
  width: 860px;
  max-width: 94vw;
  border-radius: 16px;
  border: none;
  box-shadow: 0 12px 40px rgba(31, 45, 61, 0.12);
  overflow: hidden;
}
.forgot-inner {
  display: flex;
  min-height: 480px;
}
.forgot-left {
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
.forgot-left::before,
.forgot-left::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
}
.forgot-left::before {
  width: 260px;
  height: 260px;
  right: -90px;
  top: -80px;
}
.forgot-left::after {
  width: 180px;
  height: 180px;
  left: -60px;
  bottom: -60px;
}
.forgot-logo {
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
.forgot-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 56px;
  background: var(--hj-bg-card);
}
.forgot-title {
  margin: 0 0 28px;
  font-size: 22px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.forgot-form .el-form-item {
  margin-bottom: 22px;
}
.big-input :deep(.el-input__inner) {
  font-size: 15px;
  height: 48px;
}

.forgot-btn.el-button--primary {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #2b7de0);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.forgot-btn.el-button--primary:hover {
  background: linear-gradient(135deg, #66b1ff, #409eff);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.36);
}
.forgot-btn.el-button--primary:active {
  transform: translateY(1px);
}

.tip-text {
  margin-top: 16px;
  font-size: 13px;
  color: var(--hj-text-secondary);
  line-height: 1.7;
}
.tip-text b {
  color: #e6a23c;
  font-weight: 600;
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
  .forgot-left {
    display: none;
  }
  .forgot-right {
    padding: 40px 32px;
  }
}

.forgot-footer {
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
