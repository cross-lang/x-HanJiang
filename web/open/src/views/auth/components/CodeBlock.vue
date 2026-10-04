<template>
  <div class="code-dark">
    <div class="code-dark-head">
      <span class="code-dark-tab">{{ label }}</span>
      <button class="copy-btn" @click="onCopy">
        <el-icon :size="14"><CopyDocument /></el-icon>
        <span>{{ copied ? '已复制' : '复制' }}</span>
      </button>
    </div>
    <pre class="code-dark-body"><code v-html="highlighted"></code></pre>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'
import go from 'highlight.js/lib/languages/go'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'

hljs.registerLanguage('python', python)
hljs.registerLanguage('go', go)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)

const props = defineProps<{
  /** 代码内容 */
  code: string
  /** 标签（Python / Go / cURL / JSON） */
  label: string
  /** highlight.js 语言标识（python / go / json / bash；缺省按纯文本转义展示） */
  language?: string
}>()

/** 语法高亮后的 HTML（hljs 输出已做 HTML 转义，可安全 v-html） */
const highlighted = computed(() => {
  const lang = props.language
  if (lang && hljs.getLanguage(lang)) {
    try {
      return hljs.highlight(props.code, { language: lang }).value
    } catch {
      /* fallthrough：按纯文本转义 */
    }
  }
  return escapeHtml(props.code)
})

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const copied = ref(false)

async function onCopy() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}
</script>

<style scoped>
/* ─── One Dark 深色主题代码块 + 语法高亮 ─── */
.code-dark {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #21252b;
  box-shadow: 0 4px 16px rgba(30, 31, 38, 0.1);
}
.code-dark-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #21252b;
  border-bottom: 1px solid #2c313a;
  padding: 7px 14px;
}
.code-dark-tab {
  font-size: 12.5px;
  font-weight: 600;
  color: #61afef;
  letter-spacing: 0.5px;
}
.code-dark-body {
  margin: 0;
  padding: 16px 20px;
  background: #282c34;
  font-family: var(--hj-font-mono);
  font-size: 13px;
  line-height: 1.75;
  color: #abb2bf;
  overflow-x: auto;
  user-select: text;
  white-space: pre;
  word-break: normal;
}
.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: #abb2bf;
  font-size: 12.5px;
  cursor: pointer;
  padding: 3px 8px;
  border-radius: 6px;
  transition: all 0.15s;
}
.copy-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

/* hljs token 配色（One Dark 风格；v-html 注入的 span 用 :deep 匹配） */
.code-dark-body :deep(.hljs-comment),
.code-dark-body :deep(.hljs-quote) {
  color: #5c6370;
  font-style: italic;
}
.code-dark-body :deep(.hljs-keyword),
.code-dark-body :deep(.hljs-selector-tag),
.code-dark-body :deep(.hljs-doctag) {
  color: #c678dd;
}
.code-dark-body :deep(.hljs-string),
.code-dark-body :deep(.hljs-attr),
.code-dark-body :deep(.hljs-regexp),
.code-dark-body :deep(.hljs-template-string),
.code-dark-body :deep(.hljs-addition) {
  color: #98c379;
}
.code-dark-body :deep(.hljs-number),
.code-dark-body :deep(.hljs-literal),
.code-dark-body :deep(.hljs-symbol),
.code-dark-body :deep(.hljs-bullet) {
  color: #d19a66;
}
.code-dark-body :deep(.hljs-title),
.code-dark-body :deep(.hljs-title.function_),
.code-dark-body :deep(.hljs-section) {
  color: #61afef;
}
.code-dark-body :deep(.hljs-title.class_),
.code-dark-body :deep(.hljs-type) {
  color: #e5c07b;
}
.code-dark-body :deep(.hljs-built_in),
.code-dark-body :deep(.hljs-name),
.code-dark-body :deep(.hljs-variable),
.code-dark-body :deep(.hljs-template-variable) {
  color: #e06c75;
}
.code-dark-body :deep(.hljs-params) {
  color: #d19a66;
}
.code-dark-body :deep(.hljs-meta),
.code-dark-body :deep(.hljs-meta .hljs-keyword),
.code-dark-body :deep(.hljs-meta .hljs-string) {
  color: #5c6370;
}
.code-dark-body :deep(.hljs-strong) {
  font-weight: 700;
}
.code-dark-body :deep(.hljs-emphasis) {
  font-style: italic;
}
</style>
