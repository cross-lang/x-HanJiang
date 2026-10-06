<template>
  <el-dialog v-model="dialogVisible" title="发布通知" width="600px">
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
          placeholder="通知正文，将推送至目标受众的站内信"
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
          <el-input-number
            v-model="form.duration_hours"
            :min="0.5"
            :max="720"
            :step="0.5"
            placeholder="小时数"
            class="hj-w-full"
          />
          <div class="form-tip">单位为小时（支持小数），正文将自动拼接为"预计持续 X 小时"</div>
        </el-form-item>
        <el-form-item label="维护原因">
          <el-input v-model="form.reason" placeholder="可选" />
        </el-form-item>
      </template>

      <!-- 推送范围：全体活跃用户 / 指定角色 / 指定用户 -->
      <el-form-item label="推送范围">
        <el-radio-group v-model="form.target_type">
          <el-radio value="all">全体活跃用户</el-radio>
          <el-radio value="roles">指定角色</el-radio>
          <el-radio value="users">指定用户</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="form.target_type === 'roles'" label="目标角色">
        <el-select
          v-model="form.target_roles"
          multiple
          filterable
          placeholder="选择目标角色（可多选）"
          class="hj-w-full"
          :loading="rolesLoading"
        >
          <el-option
            v-for="r in roleOptions"
            :key="r.role_code"
            :label="`${r.role_name}（${r.role_code}）`"
            :value="r.role_code"
          />
        </el-select>
      </el-form-item>
      <el-form-item v-if="form.target_type === 'users'" label="目标用户">
        <el-select
          v-model="form.target_user_ids"
          multiple
          filterable
          remote
          reserve-keyword
          placeholder="输入用户名/姓名搜索用户（可多选）"
          class="hj-w-full"
          :loading="usersLoading"
          :remote-method="searchUsers"
        >
          <el-option
            v-for="u in userOptions"
            :key="u.id"
            :label="`${u.username}（${u.name || u.username}）`"
            :value="u.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="强推渠道">
        <el-checkbox-group v-model="form.push_channels">
          <el-checkbox value="email">邮件</el-checkbox>
          <el-checkbox value="dingtalk">钉钉</el-checkbox>
          <el-checkbox value="feishu">飞书</el-checkbox>
        </el-checkbox-group>
        <div class="form-tip">站内信默认推送目标受众；勾选后额外向已配置对应渠道的用户强推</div>
      </el-form-item>
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
import { listRoles } from '@/api/role'
import { listUsers } from '@/api/user'
import type { RoleItem } from '@/types/role'
import type { UserItem } from '@/types/user'
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
  duration_hours: number | null
  reason: string
  push_channels: string[]
  target_type: 'all' | 'roles' | 'users'
  target_roles: string[]
  target_user_ids: number[]
}>({
  notice_type: 'notice',
  title: '',
  content: '',
  maintenance_time: '',
  duration_hours: null,
  reason: '',
  push_channels: [],
  target_type: 'all',
  target_roles: [],
  target_user_ids: [],
})

/** 角色下拉选项（全量加载，角色数量少） */
const roleOptions = ref<RoleItem[]>([])
const rolesLoading = ref(false)
/** 用户下拉选项（远程搜索，避免一次拉全量用户） */
const userOptions = ref<UserItem[]>([])
const usersLoading = ref(false)

/** 加载角色列表（弹窗打开时拉一次） */
async function loadRoles() {
  rolesLoading.value = true
  try {
    const res = await listRoles({ page: 1, page_size: 200 })
    const data = res.data as RoleItem[] | { items: RoleItem[] }
    roleOptions.value = Array.isArray(data) ? data : data.items || []
  } catch {
    /* 角色列表加载失败不阻塞发布 */
  } finally {
    rolesLoading.value = false
  }
}

/** 远程搜索用户（按用户名/姓名模糊匹配） */
async function searchUsers(keyword: string) {
  usersLoading.value = true
  try {
    const res = await listUsers({ page: 1, page_size: 20, keyword: keyword || undefined })
    const data = res.data as { items: UserItem[] }
    userOptions.value = data.items || []
  } catch {
    /* 用户搜索失败保留已有选项 */
  } finally {
    usersLoading.value = false
  }
}

/** 弹窗打开时生成的幂等键（本次打开期间固定；重复提交/失败重试复用同一 key，服务端幂等去重） */
const clientRequestId = ref('')

/** 生成发布幂等键（同一弹窗提交生成的 key 相同，重复点击不会重复广播） */
function buildClientRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `pub_${Date.now()}_${Math.random().toString(36).slice(2, 12)}`
}

/** 禁止选择早于今天的日期 */
function disablePastDate(date: Date): boolean {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

/** 打开弹窗时重置表单并生成新幂等键 */
watch(
  () => props.visible,
  v => {
    if (v) {
      form.value = {
        notice_type: 'notice',
        title: '',
        content: '',
        maintenance_time: '',
        duration_hours: null,
        reason: '',
        push_channels: [],
        target_type: 'all',
        target_roles: [],
        target_user_ids: [],
      }
      clientRequestId.value = buildClientRequestId()
      loadRoles()
      searchUsers('')
    }
  },
)

async function doPublish() {
  const f = form.value
  if (!f.title.trim()) {
    ElMessage.warning('请输入通知标题')
    return
  }
  if (f.notice_type === 'maintenance' && (!f.maintenance_time.trim() || !f.duration_hours)) {
    ElMessage.warning('系统维护通知必须填写维护时间与预计时长（小时数）')
    return
  }
  if (f.notice_type === 'maintenance' && f.duration_hours != null && f.duration_hours <= 0) {
    ElMessage.warning('预计持续时长必须大于 0')
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
  if (f.target_type === 'roles' && f.target_roles.length === 0) {
    ElMessage.warning('选择"指定角色"时请至少勾选一个角色')
    return
  }
  if (f.target_type === 'users' && f.target_user_ids.length === 0) {
    ElMessage.warning('选择"指定用户"时请至少选择一个用户')
    return
  }
  publishing.value = true
  try {
    const res = await publishNotification({
      title: f.title.trim(),
      notice_type: f.notice_type,
      content: f.notice_type === 'maintenance' ? '' : f.content.trim(),
      maintenance_time: f.notice_type === 'maintenance' ? f.maintenance_time.trim() : null,
      duration_hours: f.notice_type === 'maintenance' ? f.duration_hours : null,
      reason: f.notice_type === 'maintenance' ? f.reason.trim() || null : null,
      push_channels: f.push_channels.length > 0 ? f.push_channels : undefined,
      target_type: f.target_type,
      target_roles: f.target_type === 'roles' ? f.target_roles : undefined,
      target_user_ids: f.target_type === 'users' ? f.target_user_ids : undefined,
      client_request_id: clientRequestId.value,
    })
    const sent = res.data.sent_count
    ElMessage.success(sent != null && sent > 0 ? `已发布，站内信推送完成（强推 ${sent} 人）` : '已发布')
    emit('submitted')
  } catch {
    /* 错误已由拦截器处理 */
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  margin-top: 4px;
}
</style>
