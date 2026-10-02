<template>
  <el-dialog v-model="dialogVisible" title="发布通知" width="560px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="通知类型">
        <el-radio-group v-model="form.notice_type">
          <el-radio value="notice">普通通知</el-radio>
          <el-radio value="maintenance">系统维护</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="标题">
        <el-input v-model="form.title" maxlength="200" placeholder="通知标题" />
      </el-form-item>
      <el-form-item v-if="form.notice_type !== 'maintenance'" label="正文">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="5"
          maxlength="5000"
          placeholder="通知正文，将推送至全体用户的站内信"
        />
      </el-form-item>
      <template v-if="form.notice_type === 'maintenance'">
        <el-form-item label="维护时间">
          <el-date-picker
            v-model="form.maintenance_time"
            type="datetime"
            placeholder="选择维护开始时间"
            class="hj-w-full"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:ss"
            :disabled-date="disablePastDate"
          />
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input v-model="form.duration" placeholder="如 2 小时（需包含单位）" />
        </el-form-item>
        <el-form-item label="维护原因">
          <el-input v-model="form.reason" placeholder="可选" />
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="publishing" @click="doPublish">发布</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { publishNotification } from '@/api/notification'
import type { NoticeType } from '@/types/notification'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 发布成功（父级重置分页并刷新列表） */
  submitted: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const publishing = ref(false)
const form = ref<{
  notice_type: NoticeType
  title: string
  content: string
  maintenance_time: string
  duration: string
  reason: string
}>({
  notice_type: 'notice',
  title: '',
  content: '',
  maintenance_time: '',
  duration: '',
  reason: '',
})

/** 打开弹窗时重置表单 */
watch(
  () => props.visible,
  v => {
    if (v)
      form.value = { notice_type: 'notice', title: '', content: '', maintenance_time: '', duration: '', reason: '' }
  },
)

function disablePastDate(date: Date): boolean {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

async function doPublish() {
  const f = form.value
  if (!f.title.trim()) {
    ElMessage.warning('请输入通知标题')
    return
  }
  if (f.notice_type === 'maintenance' && (!f.maintenance_time.trim() || !f.duration.trim())) {
    ElMessage.warning('系统维护通知必须填写维护时间与预计时长')
    return
  }
  if (f.notice_type === 'maintenance' && !/(小时|时|h|分钟|分|天)/.test(f.duration.trim())) {
    ElMessage.warning('预计持续时长需包含单位，如 2 小时')
    return
  }
  if (f.notice_type === 'maintenance') {
    const mt = new Date(f.maintenance_time.replace(/-/g, '/'))
    if (isNaN(mt.getTime()) || mt.getTime() <= Date.now()) {
      ElMessage.warning('维护时间不能早于当前时间')
      return
    }
  }
  if (f.notice_type !== 'maintenance' && !f.content.trim()) {
    ElMessage.warning('请输入通知正文')
    return
  }
  publishing.value = true
  try {
    const res = await publishNotification({
      title: f.title.trim(),
      notice_type: f.notice_type,
      content: f.notice_type === 'maintenance' ? '' : f.content.trim(),
      maintenance_time: f.notice_type === 'maintenance' ? f.maintenance_time.trim() : null,
      duration: f.notice_type === 'maintenance' ? f.duration.trim() : null,
      reason: f.notice_type === 'maintenance' ? f.reason.trim() || null : null,
    })
    const sent = res.data.sent_count
    ElMessage.success(sent != null ? `已发布，站内信推送完成（多渠道推送 ${sent} 人）` : '已发布')
    emit('submitted')
  } catch {
    /* 错误已由拦截器处理 */
  } finally {
    publishing.value = false
  }
}
</script>
