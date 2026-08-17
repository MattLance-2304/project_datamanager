<template>
  <div>
    <!-- 筛选栏 -->
    <el-card class="page-card filter-card">
      <el-form inline @submit.prevent="load(1)">
        <el-form-item label="关键词">
          <el-input v-model="filters.q" placeholder="文件名 / 标题 / 备注 / SHA256" clearable
            style="width: 220px" @keyup.enter="load(1)" @clear="load(1)" />
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="filters.project_id" clearable placeholder="全部" style="width: 150px" @change="load(1)">
            <el-option v-for="p in cfg.projects" :key="p.id"
              :label="`${p.code}${p.status === 'archived' ? '（已归档）' : ''}`" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="filters.category_id" clearable placeholder="全部" style="width: 130px" @change="load(1)">
            <el-option v-for="c in cfg.categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="对象">
          <el-select v-model="filters.object_id" clearable filterable placeholder="全部" style="width: 150px" @change="load(1)">
            <el-option v-for="o in cfg.objects" :key="o.id" :label="o.name" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filters.kind" clearable placeholder="全部" style="width: 120px" @change="load(1)">
            <el-option label="原始数据" value="raw" />
            <el-option label="派生数据" value="derived" />
            <el-option label="备份文件" value="backup" />
          </el-select>
        </el-form-item>
        <el-form-item label="发表状态">
          <el-select v-model="filters.used" clearable placeholder="全部" style="width: 110px" @change="load(1)">
            <el-option label="未使用" :value="false" />
            <el-option label="已用于发表" :value="true" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="filters.tag_id" clearable placeholder="全部" style="width: 120px" @change="load(1)">
            <el-option v-for="t in cfg.tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="实验日期">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
            start-placeholder="开始" end-placeholder="结束" style="width: 240px" @change="load(1)" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load(1)"><el-icon><Search /></el-icon>搜索</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工具条 -->
    <div class="toolbar">
      <el-radio-group v-model="viewMode" size="small">
        <el-radio-button value="table"><el-icon><Grid /></el-icon> 表格</el-radio-button>
        <el-radio-button value="card"><el-icon><Menu /></el-icon> 缩略图</el-radio-button>
      </el-radio-group>
      <span class="total">共 {{ total }} 条</span>
      <template v-if="selected.length">
        <el-button size="small" @click="batchDownload"><el-icon><Download /></el-icon>打包下载</el-button>
        <el-button size="small" @click="batchProjectVisible = true"><el-icon><FolderAdd /></el-icon>改项目</el-button>
        <el-button size="small" @click="batchMarkUsed"><el-icon><Finished /></el-icon>标记已用</el-button>
        <el-button size="small" type="danger" @click="batchDelete"><el-icon><Delete /></el-icon>删除</el-button>
        <span class="selected-count">已选 {{ selected.length }} 条</span>
      </template>
    </div>

    <!-- 表格视图 -->
    <el-card v-if="viewMode === 'table'" class="page-card">
      <el-table :data="rows" v-loading="loading" @selection-change="(v) => (selected = v)"
        row-key="id" @row-click="goDetail">
        <el-table-column type="selection" width="42" />
        <el-table-column label="预览" width="64">
          <template #default="{ row }">
            <Thumb :record-id="row.id" :has-thumb="row.has_thumb" :filename="row.original_name" :size="44" />
          </template>
        </el-table-column>
        <el-table-column label="文件 / 标题" min-width="240">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="fname">{{ row.original_name }}</span>
              <span v-if="row.title" class="ftitle">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="88">
          <template #default="{ row }">
            <el-tag size="small" :type="KIND_TAG[row.kind]" effect="plain">{{ KIND_LABEL[row.kind] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.category_name" size="small" :color="row.category_color"
              :style="{ color: '#fff', borderColor: row.category_color }" effect="dark">
              {{ row.category_name }}
            </el-tag>
            <span v-else class="dim">-</span>
          </template>
        </el-table-column>
        <el-table-column label="项目（可直接改）" width="170">
          <template #default="{ row }">
            <span @click.stop>
              <el-select :model-value="row.project_id" size="small" clearable filterable
                placeholder="未归属" class="project-select" @change="(v) => quickProject(row, v)">
                <el-option v-for="p in cfg.activeProjects" :key="p.id" :label="p.code" :value="p.id" />
              </el-select>
            </span>
          </template>
        </el-table-column>
        <el-table-column label="对象" prop="object_name" width="120">
          <template #default="{ row }">{{ row.object_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="实验日期" width="105">
          <template #default="{ row }">{{ row.recorded_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatBytes(row.size) }}</template>
        </el-table-column>
        <el-table-column label="发表" width="90">
          <template #default="{ row }">
            <el-tooltip v-if="row.used_in_pub" :content="`已用于：${row.publication_ref}`" placement="top">
              <el-tag size="small" type="success">已用</el-tag>
            </el-tooltip>
            <el-tag v-else size="small" type="info" effect="plain">未用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传人" prop="creator_name" width="90" />
        <el-table-column label="上传时间" width="140">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="goDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click.stop="download(row)">下载</el-button>
            <el-button link type="danger" size="small" @click.stop="removeOne(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 卡片视图 -->
    <div v-else v-loading="loading" class="card-grid">
      <el-card v-for="row in rows" :key="row.id" class="record-card" shadow="hover" @click="goDetail(row)">
        <Thumb :record-id="row.id" :has-thumb="row.has_thumb" :filename="row.original_name"
          :size="180" fit="contain" class="card-thumb" />
        <div class="card-name" :title="row.original_name">{{ row.original_name }}</div>
        <div class="card-tags">
          <el-tag size="small" :type="KIND_TAG[row.kind]" effect="plain">{{ KIND_LABEL[row.kind] }}</el-tag>
          <el-tag v-if="row.category_name" size="small" :color="row.category_color"
            :style="{ color: '#fff', borderColor: row.category_color }" effect="dark">
            {{ row.category_name }}
          </el-tag>
          <el-tag v-if="row.used_in_pub" size="small" type="success">已用</el-tag>
        </div>
        <div class="card-info">
          <span>{{ row.project_code || '未归属' }}</span>
          <span>{{ formatBytes(row.size) }}</span>
        </div>
      </el-card>
      <el-empty v-if="!rows.length && !loading" description="没有符合条件的数据" />
    </div>

    <div class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
        layout="total, prev, pager, next, sizes" :page-sizes="[20, 50, 100]"
        @current-change="load()" @size-change="(s) => { pageSize = s; load(1) }" />
    </div>

    <!-- 批量改项目 -->
    <el-dialog v-model="batchProjectVisible" title="批量修改项目归属" width="420px">
      <el-select v-model="batchProjectId" clearable placeholder="选择目标项目" style="width: 100%">
        <el-option v-for="p in cfg.activeProjects" :key="p.id"
          :label="`${p.code}${p.name && p.name !== p.code ? ' · ' + p.name : ''}`" :value="p.id" />
      </el-select>
      <template #footer>
        <el-button @click="batchProjectVisible = false">取消</el-button>
        <el-button type="primary" @click="batchProject">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errMsg } from '../api'
import { useConfigStore } from '../stores/config'
import { formatBytes, formatDateTime, KIND_LABEL, KIND_TAG, tokenUrl } from '../utils'
import Thumb from '../components/Thumb.vue'

const router = useRouter()
const cfg = useConfigStore()

const filters = reactive({
  q: '', project_id: null, category_id: null, object_id: null,
  kind: null, used: null, tag_id: null,
})
const dateRange = ref(null)
const viewMode = ref('table')
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const selected = ref([])

const batchProjectVisible = ref(false)
const batchProjectId = ref(null)

onMounted(async () => {
  await cfg.ensureLoaded()
  if (router.currentRoute.value.query.project_id) {
    filters.project_id = Number(router.currentRoute.value.query.project_id)
  }
  await load(1)
})

async function load(p) {
  if (p) page.value = p
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    for (const k of ['q', 'project_id', 'category_id', 'object_id', 'kind', 'used', 'tag_id']) {
      if (filters[k] !== null && filters[k] !== '') params[k] = filters[k]
    }
    if (dateRange.value?.length === 2) {
      params.recorded_from = dateRange.value[0]
      params.recorded_to = dateRange.value[1]
    }
    const { data } = await api.get('/records', { params })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}

function reset() {
  filters.q = ''
  filters.project_id = null
  filters.category_id = null
  filters.object_id = null
  filters.kind = null
  filters.used = null
  filters.tag_id = null
  dateRange.value = null
  load(1)
}

function goDetail(row, _column, event) {
  // 点击行内的选择器 / 复选框不触发跳转
  if (event?.target?.closest?.('.el-select, .el-select__wrapper, .el-checkbox, .el-popper')) return
  router.push(`/records/${row.id}`)
}

function download(row) {
  window.open(tokenUrl(`/api/records/${row.id}/download`), '_blank')
}

async function quickProject(row, projectId) {
  const pid = projectId === '' || projectId === undefined ? null : projectId
  try {
    await api.patch(`/records/${row.id}`, { project_id: pid })
    row.project_id = pid
    row.project_code = cfg.projectById(pid)?.code || null
    ElMessage.success('项目归属已更新')
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function removeOne(row) {
  await ElMessageBox.confirm(`确定将「${row.original_name}」移入回收站？`, '删除确认', { type: 'warning' })
  try {
    await api.post(`/records/${row.id}/delete`)
    ElMessage.success('已移入回收站')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

function batchDownload() {
  const ids = selected.value.map((r) => r.id).join(',')
  window.open(tokenUrl(`/api/records/batch/zip?ids=${ids}`), '_blank')
}

async function batchProject() {
  const pid = batchProjectId.value === '' || batchProjectId.value === undefined ? null : batchProjectId.value
  try {
    await api.post('/records/batch', {
      ids: selected.value.map((r) => r.id), action: 'project', project_id: pid,
    })
    ElMessage.success('批量修改完成')
    batchProjectVisible.value = false
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function batchMarkUsed() {
  let ref
  try {
    ({ value: ref } = await ElMessageBox.prompt(
      '将所选数据标记为已用于发表，请填写出处（论文 / 图号），如「论文X Fig.3B」',
      '标记已用', { inputPlaceholder: '发表出处（必填）', inputValidator: (v) => !!v?.trim() || '必须填写出处' }))
  } catch { return }
  try {
    await api.post('/records/batch', {
      ids: selected.value.map((r) => r.id), action: 'mark_used', publication_ref: ref.trim(),
    })
    ElMessage.success('已标记')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function batchDelete() {
  await ElMessageBox.confirm(`确定将所选 ${selected.value.length} 条数据移入回收站？`, '批量删除', { type: 'warning' })
  try {
    await api.post('/records/batch', { ids: selected.value.map((r) => r.id), action: 'delete' })
    ElMessage.success('已移入回收站')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}
</script>

<style scoped>
.filter-card :deep(.el-form-item) { margin-bottom: 8px; margin-right: 12px; }
.toolbar {
  display: flex; align-items: center; gap: 10px; margin: 12px 0;
}
.total { color: #909399; font-size: 13px; }
.selected-count { color: #409eff; font-size: 13px; }
.name-cell { display: flex; flex-direction: column; min-width: 0; }
.fname { color: #303133; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ftitle { color: #909399; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dim { color: #c0c4cc; }
.project-select { width: 140px; }
.card-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px;
}
.record-card { cursor: pointer; }
.card-thumb { width: 100%; margin-bottom: 8px; }
.card-name {
  font-size: 13px; color: #303133; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; margin-bottom: 6px;
}
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px; }
.card-info { display: flex; justify-content: space-between; color: #909399; font-size: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
