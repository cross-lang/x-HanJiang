<template>
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑公告' : '新建公告'" width="760px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="200" placeholder="公告标题" />
      </el-form-item>
      <el-form-item label="展示位置" required>
        <el-radio-group v-model="form.position">
          <el-radio value="board">首页板块</el-radio>
          <el-radio value="banner">首页横幅</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="正文格式" required>
        <el-radio-group v-model="form.content_type">
          <el-radio value="markdown">Markdown</el-radio>
          <el-radio value="richtext">富文本</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="正文" required>
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="10"
          maxlength="20000"
          :placeholder="form.content_type === 'richtext' ? '输入 HTML 富文本内容' : '支持 Markdown 语法'"
        />
        <div v-if="form.content" class="hj-mt-8">
          <el-divider content-position="left">预览</el-divider>
          <div class="announcement-preview" v-html="previewHtml" />
        </div>
      </el-form-item>
      <el-form-item label="有效期" required>
        <el-date-picker
          v-model="form.start_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="开始时间"
          style="width: 240px; margin-right: 8px"
        />
        <el-date-picker
          v-model="form.end_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="结束时间"
          style="width: 240px"
        />
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        <span class="hj-text-gray hj-text-12 hj-ml-8">数值越小越靠前</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { renderAnnouncement } from '@/utils/announcement'
import { createAnnouncement, updateAnnouncement } from '@/api/announcement'
import type { AnnouncementItem, AnnouncementFormPayload } from '@/types/announcement'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** create=新建 / edit=编辑 */
  mode: 'create' | 'edit'
  /** 编辑时的原记录 */
  record?: AnnouncementItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  /** 保存成功（父级刷新列表） */
  submitted: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const isEdit = computed(() => props.mode === 'edit')
const saving = ref(false)
const form = ref<AnnouncementFormPayload>({
  title: '',
  content: '',
  content_type: 'markdown',
  position: 'board',
  start_at: '',
  end_at: '',
  sort_order: 0,
})

const previewHtml = computed(() => renderAnnouncement(form.value.content || '', form.value.content_type))

/** 打开弹窗时按模式初始化表单 */
watch(
  () => props.visible,
  v => {
    if (!v) return
    if (props.mode === 'edit' && props.record) {
      form.value = {
        title: props.record.title,
        content: props.record.content,
        content_type: props.record.content_type,
        position: props.record.position,
        start_at: props.record.start_at || '',
        end_at: props.record.end_at || '',
        sort_order: props.record.sort_order,
      }
    } else {
      form.value = {
        title: '',
        content: '',
        content_type: 'markdown',
        position: 'board',
        start_at: '',
        end_at: '',
        sort_order: 0,
      }
    }
  },
)

function validate(): boolean {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入公告标题')
    return false
  }
  if (!form.value.content.trim()) {
    ElMessage.warning('请输入公告正文')
    return false
  }
  if (!form.value.start_at || !form.value.end_at) {
    ElMessage.warning('请设置公告有效期')
    return false
  }
  if (new Date(form.value.end_at) <= new Date(form.value.start_at)) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return false
  }
  return true
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const body = {
      title: form.value.title.trim(),
      content: form.value.content,
      content_type: form.value.content_type,
      position: form.value.position,
      start_at: form.value.start_at,
      end_at: form.value.end_at,
      sort_order: form.value.sort_order,
    }
    if (isEdit.value && props.record) {
      await updateAnnouncement(props.record.id, body)
      ElMessage.success('已保存')
    } else {
      await createAnnouncement(body)
      ElMessage.success('已创建，可在草稿中发布')
    }
    emit('submitted')
  } catch {
    /* 拦截器已处理 */
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.announcement-preview {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 12px;
  max-height: 300px;
  overflow: auto;
  line-height: 1.6;
}
.announcement-preview :deep(h1),
.announcement-preview :deep(h2),
.announcement-preview :deep(h3) {
  margin: 8px 0;
}
.announcement-preview :deep(p) {
  margin: 6px 0;
}
.announcement-preview :deep(code) {
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 3px;
}
.announcement-preview :deep(pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
}
</style>
