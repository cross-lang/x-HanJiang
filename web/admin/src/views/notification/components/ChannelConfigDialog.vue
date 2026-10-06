<template>
  <el-dialog v-model="dialogVisible" title="编辑渠道配置" width="500px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="渠道">
        <el-input :model-value="channelName" disabled />
      </el-form-item>
      <el-form-item label="配置JSON">
        <el-input v-model="configText" type="textarea" :rows="8" placeholder='{"webhook": "https://..."}' />
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="form.enabled" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { updateNotificationConfig } from '@/api/notification'
import type { NotificationConfig } from '@/types/notification'

const CHANNEL_NAMES: Record<string, string> = {
  dingtalk: '钉钉群机器人',
  feishu: '飞书群机器人',
  email: 'SMTP邮件',
}

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** 编辑的渠道原配置 */
  record?: NotificationConfig | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 保存成功（父级刷新配置列表） */
  saved: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const form = ref<Partial<NotificationConfig>>({})
/** 配置 JSON 文本中间态（textArea 编辑，保存时解析为对象） */
const configText = ref('{}')

const channelName = computed(() => (form.value.channel ? CHANNEL_NAMES[form.value.channel] || form.value.channel : ''))

/** 打开弹窗时回填配置 */
watch(
  () => props.visible,
  v => {
    if (v && props.record) {
      form.value = { ...props.record }
      configText.value = props.record.config ? JSON.stringify(props.record.config, null, 2) : '{}'
    }
  },
)

async function save() {
  if (!form.value.channel) return
  let config: Record<string, unknown>
  try {
    config = JSON.parse(configText.value || '{}')
  } catch {
    ElMessage.error('配置 JSON 格式不正确')
    return
  }
  try {
    await updateNotificationConfig(form.value.channel, { config, enabled: !!form.value.enabled })
    ElMessage.success('已保存')
    emit('saved')
  } catch {
    /* ignore */
  }
}
</script>
