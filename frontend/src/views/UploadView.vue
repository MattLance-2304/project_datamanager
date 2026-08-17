<template>
  <div class="upload-page">
    <el-row :gutter="16">
      <!-- 左：文件队列 -->
      <el-col :span="12">
        <el-card class="page-card">
          <template #header>
            <div class="card-header">
              <span>① 选择文件</span>
              <el-button size="small" @click="clearDone">清除已完成</el-button>
            </div>
          </template>

          <el-upload
            drag multiple :auto-upload="false" :show-file-list="false"
            :on-change="onFileAdd" accept=""
          >
            <el-icon :size="42" color="#909399"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持任意格式（WB 凝胶图 / qPCR 数据 / 病理切片 .scn/.ndpi/.svs 等）；
                大文件自动分片上传，相同内容秒传
              </div>
            </template>
          </el-upload>

          <div class="file-queue">
            <div v-for="(f, idx) in files" :key="f.uid" class="file-row">
              <el-icon class="file-icon"><Document /></el-icon>
              <div class="file-info">
                <div class="file-name" :title="f.name">{{ f.name }}</div>
                <el-progress
                  v-if="f.status !== 'waiting'"
                  :percentage="f.progress" :status="progressStatus(f)" :stroke-width="6"
                />
              </div>
              <div class="file-meta">
                <span class="size">{{ formatBytes(f.size) }}</span>
                <el-tag v-if="f.status === 'instant'" size="small" type="success">秒传</el-tag>
                <el-tag v-else-if="f.status === 'done'" size="small" type="success">完成</el-tag>
                <el-tag v-else-if="f.status === 'error'" size="small" type="danger">失败</el-tag>
                <el-icon class="remove" @click="files.splice(idx, 1)"><CircleClose /></el-icon>
              </div>
            </div>
            <el-empty v-if="!files.length" description="尚未选择文件" :image-size="70" />
          </div>
        </el-card>
      </el-col>

      <!-- 右：元数据表单 -->
      <el-col :span="12">
        <el-card class="page-card">
          <template #header><span>② 填写元数据（对本次全部文件生效）</span></template>

          <el-form label-width="92px" label-position="right">
            <el-form-item label="数据类型">
              <el-radio-group v-model="form.kind">
                <el-radio-button value="raw">原始数据</el-radio-button>
                <el-radio-button value="derived">派生数据</el-radio-button>
                <el-radio-button value="backup">备份文件</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <template v-if="form.kind === 'derived'">
              <el-form-item label="父文件" required>
                <el-select
                  v-model="form.parent_record_id" filterable remote :remote-method="searchParents"
                  :loading="parentLoading" placeholder="输入文件名 / 标题搜索原始数据"
                  style="width: 100%"
                >
                  <el-option v-for="p in parentOptions" :key="p.id"
                    :label="`#${p.id} ${p.original_name}${p.title ? ' · ' + p.title : ''}`" :value="p.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="派生说明">
                <el-input v-model="form.derive_note" placeholder="如：GAPDH 条带截取 / 200x 放大 / 裁剪自图A" />
              </el-form-item>
            </template>

            <el-form-item label="所属项目">
              <el-select v-model="form.project_id" clearable placeholder="未归属" style="width: 100%">
                <el-option v-for="p in cfg.activeProjects" :key="p.id"
                  :label="`${p.code}${p.name && p.name !== p.code ? ' · ' + p.name : ''}`" :value="p.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="实验分类">
              <el-select v-model="form.category_id" clearable placeholder="选择分类" style="width: 100%">
                <el-option v-for="c in cfg.activeCategories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>

            <!-- 分类联动动态渲染的自定义字段 -->
            <MetaFields v-model="form.custom_values" :fields="fields" />

            <el-form-item label="实验对象">
              <el-select
                v-model="form.object_name" filterable clearable allow-create default-first-option
                placeholder="什么细胞 / 动物 / 组织，可输入新建" style="width: 100%"
              >
                <el-option v-for="o in cfg.objects" :key="o.id"
                  :label="`${o.name}（${OBJECT_KIND_LABEL[o.kind] || '其他'}）`" :value="o.name" />
              </el-select>
            </el-form-item>

            <el-form-item label="实验日期">
              <el-date-picker v-model="form.recorded_date" type="date" value-format="YYYY-MM-DD"
                placeholder="数据记录日期" style="width: 100%" />
            </el-form-item>

            <el-form-item label="标题">
              <el-input v-model="form.title" placeholder="简要标题（可选）" />
            </el-form-item>

            <el-form-item label="标签">
              <el-select v-model="form.tag_names" multiple filterable allow-create default-first-option
                placeholder="回车添加标签" style="width: 100%">
                <el-option v-for="t in cfg.tags" :key="t.id" :label="t.name" :value="t.name" />
              </el-select>
            </el-form-item>

            <el-form-item label="备注">
              <el-input v-model="form.note" type="textarea" :rows="2" placeholder="实验条件、分组等（可选）" />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <div class="submit-bar">
      <div class="hint">
        已选 {{ files.length }} 个文件
        <template v-if="form.kind === 'derived'">，将作为派生数据关联到父文件</template>
      </div>
      <el-button type="primary" size="large" :loading="submitting" :disabled="!files.length" @click="submitAll">
        {{ submitting ? '正在上传…' : '开始上传' }}
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { sha256 } from 'js-sha256'
import api, { errMsg } from '../api'
import { useConfigStore } from '../stores/config'
import { formatBytes, OBJECT_KIND_LABEL } from '../utils'
import MetaFields from '../components/MetaFields.vue'

const route = useRoute()
const router = useRouter()
const cfg = useConfigStore()

const files = ref([]) // {uid, name, size, raw, status, progress}
const submitting = ref(false)

const form = reactive({
  kind: 'raw',
  parent_record_id: null,
  derive_note: '',
  project_id: null,
  category_id: null,
  object_name: '',
  recorded_date: null,
  title: '',
  note: '',
  tag_names: [],
  custom_values: {},
})

const fields = ref([])
const parentOptions = ref([])
const parentLoading = ref(false)

onMounted(async () => {
  await cfg.ensureLoaded()
  if (route.query.parent) {
    form.kind = 'derived'
    form.parent_record_id = Number(route.query.parent)
    try {
      const { data } = await api.get(`/records/${route.query.parent}`)
      parentOptions.value = [data.record]
    } catch { /* ignore */ }
  }
})

async function loadFields() {
  fields.value = form.category_id ? await cfg.loadFields(form.category_id) : []
}

// 分类变化时重新加载该分类的自定义字段
watch(() => form.category_id, loadFields, { immediate: true })

function onFileAdd(file) {
  files.value.push({
    uid: file.uid, name: file.name, size: file.size, raw: file.raw,
    status: 'waiting', progress: 0,
  })
}

function clearDone() {
  files.value = files.value.filter((f) => f.status !== 'done' && f.status !== 'instant')
}

function progressStatus(f) {
  if (f.status === 'error') return 'exception'
  if (f.status === 'done' || f.status === 'instant') return 'success'
  return undefined
}

async function sha256File(fileObj) {
  const hasher = sha256.create()
  const chunk = 8 * 1024 * 1024
  if (fileObj.size === 0) return hasher.hex()
  for (let off = 0; off < fileObj.size; off += chunk) {
    const buf = await fileObj.raw.slice(off, off + chunk).arrayBuffer()
    hasher.update(buf)
  }
  return hasher.hex()
}

async function uploadOne(f) {
  // 小文件先查秒传
  if (f.size <= 512 * 1024 * 1024) {
    try {
      const hash = await sha256File(f)
      const { data } = await api.post('/uploads/check-hash', { sha256: hash })
      if (data.exists) {
        f.status = 'instant'
        f.progress = 100
        return data.file_id
      }
    } catch { /* 校验失败不影响正常上传 */ }
  }
  const { data: init } = await api.post('/uploads', { filename: f.name, size: f.size })
  const chunkSize = init.chunk_size
  const total = Math.max(1, Math.ceil(f.size / chunkSize))
  for (let i = 0; i < total; i++) {
    const blob = f.raw.slice(i * chunkSize, (i + 1) * chunkSize)
    await api.put(`/uploads/${init.upload_id}/${i}`, blob, {
      headers: { 'Content-Type': 'application/octet-stream' },
    })
    f.progress = Math.round(((i + 1) / total) * 95)
  }
  const { data: done } = await api.post(`/uploads/${init.upload_id}/complete`)
  f.progress = 100
  f.status = 'done'
  return done.file_id
}

async function searchParents(q) {
  if (!q) { parentOptions.value = []; return }
  parentLoading.value = true
  try {
    const { data } = await api.get('/records', { params: { q, page_size: 20 } })
    parentOptions.value = data.items
  } finally {
    parentLoading.value = false
  }
}

function validate() {
  if (form.kind === 'derived' && !form.parent_record_id) return '派生数据必须选择父文件'
  for (const f of fields.value) {
    const v = form.custom_values[f.field_key]
    if (f.is_required && (v === undefined || v === null || v === '')) return `必填字段「${f.label}」未填写`
  }
  return null
}

async function submitAll() {
  const err = validate()
  if (err) return ElMessage.warning(err)
  submitting.value = true
  try {
    const fileIds = []
    for (const f of files.value) {
      if (f.status === 'done' || f.status === 'instant') continue
      f.status = 'uploading'
      try {
        fileIds.push(await uploadOne(f))
      } catch (e) {
        f.status = 'error'
        throw new Error(`${f.name} 上传失败：${errMsg(e)}`)
      }
    }
    if (!fileIds.length) return ElMessage.info('没有新文件需要上传')

    // 解析动态创建的对象与标签
    let objectId = null
    if (form.object_name) {
      const obj = await cfg.findOrCreateObject(form.object_name.trim())
      objectId = obj.id
    }
    const tagIds = []
    for (const name of form.tag_names) {
      const t = await cfg.findOrCreateTag(name.trim())
      tagIds.push(t.id)
    }

    const payload = {
      file_ids: fileIds,
      kind: form.kind,
      parent_record_id: form.kind === 'derived' ? form.parent_record_id : null,
      derive_note: form.derive_note,
      project_id: form.project_id === '' ? null : form.project_id,
      category_id: form.category_id === '' ? null : form.category_id,
      object_id: objectId,
      recorded_date: form.recorded_date,
      title: form.title,
      note: form.note,
      custom_values: form.custom_values,
      tag_ids: tagIds,
    }
    const { data } = await api.post('/records', payload)

    let msg = `成功入库 ${data.items.length} 条数据`
    if (data.warnings?.length) msg += '\n' + data.warnings.join('\n')
    await ElMessageBox.alert(msg, '上传完成', {
      type: data.warnings?.length ? 'warning' : 'success',
      confirmButtonText: '去查看',
      cancelButtonText: '留在本页',
      showCancelButton: true,
    }).then(() => router.push('/browse')).catch(() => {})
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.file-queue { margin-top: 12px; max-height: 420px; overflow: auto; }
.file-row {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px;
  border: 1px solid #ebeef5; border-radius: 6px; margin-bottom: 8px;
}
.file-icon { font-size: 20px; color: #409eff; flex-shrink: 0; }
.file-info { flex: 1; min-width: 0; }
.file-name {
  font-size: 13px; color: #303133; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; margin-bottom: 2px;
}
.file-meta { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.size { font-size: 12px; color: #909399; }
.remove { color: #c0c4cc; cursor: pointer; }
.remove:hover { color: #f56c6c; }
.submit-bar {
  position: sticky; bottom: 0; background: #f5f7fa; padding: 12px 4px;
  display: flex; justify-content: space-between; align-items: center;
}
.hint { color: #606266; font-size: 14px; }
</style>
