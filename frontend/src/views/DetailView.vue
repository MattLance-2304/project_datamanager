<template>
  <div v-if="record" v-loading="loading">
    <div class="detail-head">
      <div class="head-left">
        <el-button link @click="router.back()"><el-icon><ArrowLeft /></el-icon>返回</el-button>
        <h2 class="title">{{ record.original_name }}</h2>
        <el-tag :type="KIND_TAG[record.kind]" effect="plain">{{ KIND_LABEL[record.kind] }}</el-tag>
        <el-tag v-if="record.used_in_pub" type="success">已用于发表：{{ record.publication_ref }}</el-tag>
      </div>
      <div class="head-actions">
        <el-button :disabled="!previewOk" @click="openPreview">
          <el-icon><ZoomIn /></el-icon>预览大图
        </el-button>
        <el-button @click="download"><el-icon><Download /></el-icon>下载</el-button>
        <el-button type="primary" @click="goDerive"><el-icon><Scissor /></el-icon>上传派生文件</el-button>
        <el-button type="danger" plain @click="removeRecord"><el-icon><Delete /></el-icon>移入回收站</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左列：预览 + 派生谱系 + 审计 -->
      <el-col :span="10">
        <el-card class="page-card">
          <template #header><span>预览</span></template>
          <div class="preview-box">
            <el-image
              v-if="record.has_thumb || previewOk" :src="record.has_thumb ? thumbUrl : previewUrl"
              fit="contain" class="preview-img"
              :preview-src-list="[previewUrl]" :preview-teleported="true" hide-on-click-modal
            />
            <div v-else class="no-preview">
              <el-icon :size="46"><Picture /></el-icon>
              <p>该格式无预览（{{ ext }}），请下载后查看</p>
            </div>
          </div>
          <el-descriptions :column="1" border size="small" class="file-desc">
            <el-descriptions-item label="SHA256">
              <span class="sha">{{ record.sha256 }}</span>
              <el-button link type="primary" size="small" @click="copySha">复制</el-button>
            </el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatBytes(record.size) }}（{{ record.mime || '未知类型' }}）</el-descriptions-item>
            <el-descriptions-item label="上传人">{{ record.creator_name || '-' }} · {{ formatDateTime(record.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="page-card section">
          <template #header><span>派生谱系</span></template>
          <el-tree
            v-if="lineage.tree" :data="[lineage.tree]" :props="{ children: 'children', label: 'label' }"
            node-key="id" default-expand-all :expand-on-click-node="false"
          >
            <template #default="{ data }">
              <span class="tree-node" :class="{ current: data.is_current, deleted: data.deleted }"
                @click="data.id !== record.id && !data.deleted && router.push(`/records/${data.id}`)">
                <span class="tree-name">{{ data.original_name }}</span>
                <el-tag size="small" :type="KIND_TAG[data.kind]" effect="plain">{{ KIND_LABEL[data.kind] }}</el-tag>
                <el-tag v-if="data.used_in_pub" size="small" type="success">已用</el-tag>
                <el-tag v-if="data.deleted" size="small" type="info">回收站</el-tag>
              </span>
            </template>
          </el-tree>
          <div v-if="parent" class="parent-line">
            父文件：
            <el-link type="primary" @click="router.push(`/records/${parent.id}`)">
              #{{ parent.id }} {{ parent.original_name }}
            </el-link>
            <el-tag v-if="parent.used_in_pub" size="small" type="success" style="margin-left: 6px">
              已用于 {{ parent.publication_ref }}
            </el-tag>
          </div>
        </el-card>

        <el-card class="page-card section">
          <template #header><span>操作历史（审计）</span></template>
          <el-timeline v-if="auditLogs.length" style="padding-left: 4px">
            <el-timeline-item v-for="log in auditLogs" :key="log.id" :timestamp="`${log.user || '系统'} · ${formatDateTime(log.created_at)}`"
              :type="log.action === 'hard_delete' ? 'danger' : log.action === 'create' ? 'primary' : undefined">
              <div class="audit-action">{{ AUDIT_LABEL[log.action] || log.action }}</div>
              <div v-for="(chg, field) in log.changes || {}" :key="field" class="audit-change">
                <template v-if="chg && typeof chg === 'object' && ('old' in chg || 'new' in chg)">
                  <span class="audit-field">{{ field }}：</span>
                  <span class="audit-old">{{ fmtVal(chg.old) }}</span>
                  <el-icon><ArrowRight /></el-icon>
                  <span class="audit-new">{{ fmtVal(chg.new) }}</span>
                </template>
                <template v-else>
                  <span class="audit-field">{{ field }}：</span>
                  <span class="audit-new">{{ fmtVal(chg) }}</span>
                </template>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无记录" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 右列：元数据编辑 + 已用标记 -->
      <el-col :span="14">
        <el-card class="page-card">
          <template #header><span>元数据</span></template>
          <el-form label-width="92px">
            <el-form-item label="标题">
              <el-input v-model="editForm.title" />
            </el-form-item>
            <el-form-item label="文件名">
              <el-input v-model="editForm.original_name" />
            </el-form-item>
            <el-form-item label="所属项目">
              <el-select v-model="editForm.project_id" clearable filterable placeholder="未归属" style="width: 100%">
                <el-option v-for="p in cfg.projects.filter(x => x.status === 'active')" :key="p.id"
                  :label="`${p.code}${p.name && p.name !== p.code ? ' · ' + p.name : ''}`" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="实验分类">
              <el-select v-model="editForm.category_id" clearable placeholder="未分类" style="width: 100%">
                <el-option v-for="c in cfg.activeCategories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
            <MetaFields v-model="editForm.custom_values" :fields="customFields" />
            <el-form-item label="实验对象">
              <el-select v-model="editForm.object_name" filterable clearable allow-create default-first-option
                placeholder="什么细胞 / 动物 / 组织" style="width: 100%">
                <el-option v-for="o in cfg.objects" :key="o.id"
                  :label="`${o.name}（${OBJECT_KIND_LABEL[o.kind] || '其他'}）`" :value="o.name" />
              </el-select>
            </el-form-item>
            <el-form-item label="实验日期">
              <el-date-picker v-model="editForm.recorded_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
            <el-form-item label="标签">
              <el-select v-model="editForm.tag_names" multiple filterable allow-create default-first-option
                placeholder="回车添加" style="width: 100%">
                <el-option v-for="t in cfg.tags" :key="t.id" :label="t.name" :value="t.name" />
              </el-select>
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="editForm.note" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item v-if="record.kind === 'derived'" label="派生说明">
              <el-input :model-value="record.derive_note" disabled />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="save">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="page-card section">
          <template #header><span>发表使用标记</span></template>
          <div class="used-box">
            <el-switch v-model="usedForm.used" active-text="已用于发表" inactive-text="未使用" />
            <template v-if="usedForm.used">
              <el-input v-model="usedForm.ref" placeholder="发表出处，如：论文X Fig.3B / DOI"
                style="margin-top: 10px" />
              <div class="used-tip">标记后系统会在其谱系再次用于其他论文时给出警告，避免一图两用。</div>
            </template>
            <el-button type="primary" style="margin-top: 10px" :loading="savingUsed" @click="saveUsed">
              保存标记
            </el-button>
          </div>
        </el-card>

        <el-card v-if="children.length" class="page-card section">
          <template #header><span>派生文件（{{ children.length }}）</span></template>
          <el-table :data="children" size="small" @row-click="(r) => router.push(`/records/${r.id}`)">
            <el-table-column prop="original_name" label="文件名" min-width="180" />
            <el-table-column prop="derive_note" label="派生说明" min-width="140" />
            <el-table-column label="已用" width="150">
              <template #default="{ row }">
                <span v-if="row.used_in_pub">{{ row.publication_ref }}</span>
                <span v-else class="dim">未使用</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.deleted" size="small" type="info">回收站</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errMsg } from '../api'
import { useConfigStore } from '../stores/config'
import {
  formatBytes, formatDateTime, tokenUrl, extOf,
  KIND_LABEL, KIND_TAG, OBJECT_KIND_LABEL, AUDIT_LABEL,
} from '../utils'
import MetaFields from '../components/MetaFields.vue'

const route = useRoute()
const router = useRouter()
const cfg = useConfigStore()

const record = ref(null)
const parent = ref(null)
const children = ref([])
const customFields = ref([])
const lineage = ref({})
const auditLogs = ref([])
const loading = ref(false)

const editForm = reactive({
  title: '', original_name: '', project_id: null, category_id: null,
  object_name: '', recorded_date: null, note: '', tag_names: [], custom_values: {},
})
const saving = ref(false)
const usedForm = reactive({ used: false, ref: '' })
const savingUsed = ref(false)
const previewOk = ref(true)

const thumbUrl = computed(() => tokenUrl(`/api/records/${record.value.id}/thumbnail`))
const previewUrl = computed(() => tokenUrl(`/api/records/${record.value.id}/preview`))
const ext = computed(() => extOf(record.value?.original_name).toUpperCase())

onMounted(async () => {
  await cfg.ensureLoaded()
  await load()
})

watch(() => route.params.id, () => { if (route.params.id) load() })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/records/${route.params.id}`)
    record.value = data.record
    parent.value = data.parent
    children.value = data.children
    customFields.value = data.custom_fields

    editForm.title = data.record.title
    editForm.original_name = data.record.original_name
    editForm.project_id = data.record.project_id
    editForm.category_id = data.record.category_id
    editForm.object_name = data.record.object_name || ''
    editForm.recorded_date = data.record.recorded_date
    editForm.note = data.record.note
    editForm.tag_names = [...(data.record.tags || [])]
    editForm.custom_values = { ...(data.record.custom_values || {}) }
    usedForm.used = data.record.used_in_pub
    usedForm.ref = data.record.publication_ref

    // 详情页的字段定义走强制刷新，保证"最近使用值"最新
    if (data.record.category_id) {
      customFields.value = await cfg.loadFields(data.record.category_id, { force: true })
    }

    const [lin, logs] = await Promise.all([
      api.get(`/records/${route.params.id}/lineage`),
      api.get(`/records/${route.params.id}/audit`),
    ])
    lineage.value = lin.data
    auditLogs.value = logs.data
    try {
      previewOk.value = (await api.head(`/records/${record.value.id}/preview`)).status === 200
    } catch {
      previewOk.value = false
    }
  } catch (e) {
    ElMessage.error(errMsg(e))
    router.push('/browse')
  } finally {
    loading.value = false
  }
}

function fmtVal(v) {
  if (v === null || v === undefined || v === '') return '空'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v).length > 40 ? String(v).slice(0, 40) + '…' : String(v)
}

function copySha() {
  navigator.clipboard.writeText(record.value.sha256)
  ElMessage.success('SHA256 已复制')
}

function openPreview() {
  window.open(previewUrl.value, '_blank')
}

function download() {
  window.open(tokenUrl(`/api/records/${record.value.id}/download`), '_blank')
}

function goDerive() {
  router.push({ path: '/upload', query: { parent: record.value.id } })
}

async function save() {
  saving.value = true
  try {
    const tagIds = []
    for (const name of editForm.tag_names) {
      const t = await cfg.findOrCreateTag(name.trim())
      tagIds.push(t.id)
    }
    const payload = {}
    const orNull = (v) => (v === '' || v === undefined ? null : v)
    if (editForm.title !== record.value.title) payload.title = editForm.title
    if (editForm.original_name !== record.value.original_name) payload.original_name = editForm.original_name
    if (editForm.project_id !== record.value.project_id) payload.project_id = orNull(editForm.project_id)
    if (editForm.category_id !== record.value.category_id) payload.category_id = orNull(editForm.category_id)
    if (editForm.recorded_date !== record.value.recorded_date) payload.recorded_date = editForm.recorded_date || null
    if (editForm.note !== record.value.note) payload.note = editForm.note
    payload.custom_values = editForm.custom_values
    payload.tag_ids = tagIds
    if (editForm.object_name) {
      const obj = await cfg.findOrCreateObject(editForm.object_name.trim())
      payload.object_id = obj.id
    } else {
      payload.object_id = null
    }
    await api.patch(`/records/${record.value.id}`, payload)
    ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    saving.value = false
  }
}

async function saveUsed() {
  if (usedForm.used && !usedForm.ref?.trim()) return ElMessage.warning('请填写发表出处')
  savingUsed.value = true
  try {
    let warnings = []
    if (usedForm.used) {
      const { data } = await api.post(`/records/${record.value.id}/mark-used`,
        { publication_ref: usedForm.ref.trim() })
      warnings = data.warnings || []
    } else {
      await api.post(`/records/${record.value.id}/unmark-used`)
    }
    if (warnings.length) {
      await ElMessageBox.alert(warnings.join('\n'), '重复使用警告', { type: 'warning' })
    } else {
      ElMessage.success('已保存')
    }
    await load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    savingUsed.value = false
  }
}

async function removeRecord() {
  await ElMessageBox.confirm(`确定将「${record.value.original_name}」移入回收站？`, '删除确认', { type: 'warning' })
  try {
    await api.post(`/records/${record.value.id}/delete`)
    ElMessage.success('已移入回收站')
    router.push('/browse')
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}
</script>

<style scoped>
.detail-head {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;
}
.head-left { display: flex; align-items: center; gap: 10px; }
.head-left .title { font-size: 18px; margin: 0; max-width: 480px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.section { margin-top: 14px; }
.preview-box {
  display: flex; align-items: center; justify-content: center;
  background: #f5f7fa; border-radius: 6px; min-height: 300px; padding: 10px;
}
.preview-img { width: 100%; max-height: 420px; }
.no-preview { color: #909399; text-align: center; }
.file-desc { margin-top: 12px; }
.sha { font-family: Consolas, monospace; font-size: 12px; word-break: break-all; }
.tree-node { display: flex; align-items: center; gap: 6px; cursor: pointer; }
.tree-node.current { color: #409eff; font-weight: 600; }
.tree-node.deleted { color: #c0c4cc; text-decoration: line-through; }
.tree-name { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.parent-line { margin-top: 8px; color: #606266; font-size: 13px; }
.audit-action { font-weight: 600; color: #303133; }
.audit-change { display: flex; align-items: center; gap: 4px; font-size: 12px; margin-top: 2px; flex-wrap: wrap; }
.audit-field { color: #909399; }
.audit-old { color: #f56c6c; text-decoration: line-through; }
.audit-new { color: #67c23a; }
.used-box { padding: 4px 2px; }
.used-tip { color: #909399; font-size: 12px; margin-top: 8px; }
.dim { color: #c0c4cc; }
</style>
