<template>
  <div class="auth-page">
    <!-- 模块头 -->
    <PageHead
      crumbs="认证和授权 / 鉴权模式"
      title="鉴权模式"
      desc="开放接口面向外部应用，鉴权与门户自身会话登录（JWT + Redis）完全隔离。调用方应用经管理端审批通过后，凭应用凭证 + HanJiang-1 签名调用。"
    />

    <AuthAnchorNav :anchors="anchors" />

    <!-- 鉴权模式：三卡对比 -->
    <section id="modes" class="auth-card">
      <h3 class="auth-card-title">三种鉴权模式</h3>
      <p class="auth-lead">
        开放接口 <code>/api/open/v1</code> 支持三种鉴权模式，按应用 <code>auth_mode</code> 分流：
      </p>
      <div class="mode-grid">
        <div
          v-for="m in modes"
          :key="m.mode"
          class="mode-card"
          :class="{ 'mode-card-rec': m.rec }"
        >
          <div class="mode-card-top">
            <code class="mode-card-name">{{ m.mode }}</code>
            <span v-if="m.tag" class="mode-card-tag" :class="`tag-${m.mode}`">{{ m.tag }}</span>
          </div>
          <div class="mode-card-cred">{{ m.credential }}</div>
          <div class="mode-card-row">
            <span class="mode-card-row-label">适用场景</span>
            <span class="mode-card-row-value">{{ m.scenario }}</span>
          </div>
          <div class="mode-card-row">
            <span class="mode-card-row-label">何时选择</span>
            <span class="mode-card-row-value">{{ m.when }}</span>
          </div>
        </div>
      </div>
      <div class="auth-alert auth-alert-info">
        <el-icon :size="15"><InfoFilled /></el-icon>
        <span>
          生产对接推荐 <b>hmac</b> 签名模式：明文模式下 AppKey 在请求头中直接暴露，仅建议在可信内网使用。
        </span>
      </div>
    </section>

    <!-- 凭证约定 -->
    <section id="credentials" class="auth-card">
      <h3 class="auth-card-title">凭证约定</h3>
      <div class="auth-algo">
        <div v-for="t in terms" :key="t.name" class="auth-algo-row">
          <span class="auth-algo-label">{{ t.name }}</span>
          <span class="auth-algo-value">{{ t.value }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { InfoFilled } from '@element-plus/icons-vue'
import PageHead from '@/components/PageHead.vue'
import AuthAnchorNav from '@/components/AuthAnchorNav.vue'

const anchors = [
  { id: 'modes', label: '三种鉴权模式' },
  { id: 'credentials', label: '凭证约定' },
]

const modes = [
  {
    mode: 'plain',
    credential: '请求头直接携带 X-App-Id + X-App-Key（明文）',
    scenario: '可信内网 / 联调调试',
    when: '开发调试、内网服务间调用，密钥不暴露到公网',
    rec: false,
    tag: '',
  },
  {
    mode: 'hmac',
    credential: 'X-App-Id + X-App-Date + X-App-Authorization（HanJiang-1 签名）',
    scenario: '生产环境',
    when: '对外提供服务，AppKey 不出现在传输中，防重放',
    rec: true,
    tag: '推荐',
  },
  {
    mode: 'both',
    credential: '两种凭证均接受',
    scenario: '灰度迁移期',
    when: '存量客户端切到 hmac 前的过渡阶段，双凭证兼容',
    rec: false,
    tag: '',
  },
]

const terms = [
  { name: '调用前缀', value: '/api/open/v1（签名串中的 URI 必须包含此前缀）' },
  { name: 'AppId', value: '「应用管理 → 创建应用」时生成；创建后由管理端审批（pending → approved）' },
  { name: 'AppKey', value: '「应用管理 → 重置 Key」可重新生成；每次仅展示一次' },
  { name: 'scope 授权', value: '应用勾选所需 scope 提交申请，管理端审批通过后生效；未授权 scope 调用返回 403' },
  { name: '鉴权模式', value: 'plain / hmac / both，在创建应用时选择，可后续调整' },
  { name: '应用状态', value: '审批未通过（pending / rejected）或应用停用时，一律拒绝调用（403 / 401）' },
]
</script>

<style scoped>
@import '@/styles/auth-guide.css';

/* ─── 三卡对比 ─── */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.mode-card {
  border: 1px solid var(--hj-border-light);
  border-radius: var(--hj-radius-lg);
  padding: 18px;
  background: var(--hj-bg-page);
  transition: all 0.2s;
}
.mode-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(31, 45, 61, 0.08);
}
.mode-card-rec {
  border-color: var(--hj-primary);
  background: linear-gradient(180deg, #f0f7ff 0%, var(--hj-bg-card) 60%);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.12);
}
.mode-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.mode-card-name {
  font-family: var(--hj-font-mono);
  font-size: 15px;
  font-weight: 700;
  color: var(--hj-text-title);
  white-space: nowrap;
}
.mode-card-tag {
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  white-space: nowrap;
}
.tag-hmac {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
}
.mode-card-cred {
  font-size: 13px;
  color: var(--hj-text-regular);
  line-height: 1.75;
  min-height: 56px;
  margin-bottom: 12px;
}
.mode-card-row {
  padding-top: 9px;
  border-top: 1px dashed var(--hj-border-lighter);
  margin-top: 9px;
}
.mode-card-row-label {
  display: block;
  font-size: 12px;
  color: var(--hj-text-muted);
  margin-bottom: 3px;
}
.mode-card-row-value {
  font-size: 13px;
  color: var(--hj-text-title);
  line-height: 1.6;
}
</style>
