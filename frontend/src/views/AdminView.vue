<template>
  <el-tabs v-model="tab" type="border-card" class="page-card">
    <!-- ========== 项目 ========== -->
    <el-tab-pane label="项目管理" name="projects">
      <div class="pane-head">
        <el-button type="primary" size="small" @click="openProject()"><el-icon><Plus /></el-icon>新建项目</el-button>
      </div>
      <el-table :data="cfg.projects" size="small">
        <el-table-column prop="code" label="编号" width="130" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column prop="record_count" label="数据条目" width="90" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'active'" size="small" type="success">进行中</el-tag>
            <el-tag v-else size="small" type="info">已归档</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openProject(row)">编辑</el-button>
            <el-button link size="small" @click="toggleProject(row)">
              {{ row.status === 'active' ? '归档' : '恢复' }}
            </el-button>
            <el-button link type="danger" size="small" @click="deleteProject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <!-- ========== 分类与自定义字段 ========== -->
    <el-tab-pane label="实验分类" name="categories">
      <el-row :gutter="16">
        <el-col :span="9">
          <div class="pane-head">
            <el-button type="primary" size="small" @click="openCategory()"><el-icon><Plus /></el-icon>新建分类</el-button>
          </div>
          <el-table :data="cfg.categories" size="small" highlight-current-row
            @current-change="(r) => (currentCategory = r)">
            <el-table-column label="分类" width="140">
              <template #default="{ row }">
                <span class="cat-dot" :style="{ background: row.color }" />{{ row.name }}
              </template>
            </el-table-column>
            <el-table-column prop="field_count" label="字段数" width="70" />
            <el-table-column label="启用" width="60">
              <template #default="{ row }">
                <el-tag v-if="row.is_active" size="small" type="success" effect="plain">是</el-tag>
                <el-tag v-else size="small" type="info" effect="plain">否</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="60" />
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click.stop="openCategory(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click.stop="deleteCategory(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
        <el-col :span="15">
          <div class="pane-head">
            <span v-if="currentCategory">
              「{{ currentCategory.name }}」的自定义字段
              <el-button type="primary" size="small" style="margin-left: 10px"
                @click="openField()"><el-icon><Plus /></el-icon>添加字段</el-button>
            </span>
            <span v-else class="dim">← 点击左侧分类后配置其自定义字段</span>
          </div>
          <el-table v-if="currentCategory" :data="fields" size="small">
            <el-table-column prop="label" label="字段名" min-width="110" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">{{ FIELD_TYPE_LABEL[row.field_type] }}</template>
            </el-table-column>
            <el-table-column label="下拉选项" min-width="160">
              <template #default="{ row }">
                <template v-if="row.field_type === 'select'">
                  <el-tag v-for="o in row.select_options" :key="o" size="small" style="margin: 1px 3px 1px 0">{{ o }}</el-tag>
                </template>
                <span v-else class="dim">-</span>
              </template>
            </el-table-column>
            <el-table-column label="必填" width="60">
              <template #default="{ row }">{{ row.is_required ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column prop="sort_order" label="排序" width="60" />
            <el-table-column label="操作" width="130">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openField(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="deleteField(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
      </el-row>
    </el-tab-pane>

    <!-- ========== 对象库 ========== -->
    <el-tab-pane label="实验对象库" name="objects">
      <div class="pane-head">
        <el-button type="primary" size="small" @click="openObject()"><el-icon><Plus /></el-icon>新建对象</el-button>
      </div>
      <el-table :data="cfg.objects" size="small">
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="类别" width="90">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ OBJECT_KIND_LABEL[row.kind] || '其他' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="aliases" label="别名（检索用）" min-width="180" />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openObject(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteObject(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <!-- ========== 标签 ========== -->
    <el-tab-pane label="标签" name="tags">
      <div class="pane-head">
        <el-input v-model="newTagName" placeholder="新标签名" style="width: 200px" size="small" />
        <el-button type="primary" size="small" style="margin-left: 8px" @click="addTag">添加</el-button>
      </div>
      <div class="tag-wall">
        <el-tag v-for="t in cfg.tags" :key="t.id" closable style="margin: 4px" @close="deleteTag(t)">
          {{ t.name }}
        </el-tag>
        <span v-if="!cfg.tags.length" class="dim">暂无标签</span>
      </div>
    </el-tab-pane>

    <!-- ========== 用户 ========== -->
    <el-tab-pane label="用户管理" name="users">
      <div class="pane-head">
        <el-button type="primary" size="small" @click="openUser()"><el-icon><Plus /></el-icon>新建用户</el-button>
      </div>
      <el-table :data="users" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="130" />
        <el-table-column prop="display_name" label="姓名" width="130" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.role === 'admin'" size="small" type="danger">管理员</el-tag>
            <el-tag v-else size="small">成员</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openUser(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-tab-pane>

    <!-- ========== 运维 ========== -->
    <el-tab-pane label="运维（备份 / 校验 / 导出）" name="ops">
      <el-card shadow="never" class="ops-card">
        <template #header><span>数据备份（系统级，覆盖全部文件）</span></template>
        <el-form inline>
          <el-form-item label="备份模式">
            <el-radio-group v-model="backupForm.mode" @change="onBackupModeChange">
              <el-radio-button value="off">关闭</el-radio-button>
              <el-radio-button value="realtime">实时备份</el-radio-button>
              <el-radio-button value="scheduled">定时备份</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="backupForm.mode === 'scheduled'" label="每天">
            <el-time-picker v-model="backupForm.run_at" format="HH:mm" value-format="HH:mm"
              placeholder="02:00" style="width: 110px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="backupSaving" @click="saveBackupSetting">保存设置</el-button>
            <el-button :loading="backupRunning" @click="runBackupNow">立即全量备份</el-button>
          </el-form-item>
        </el-form>
        <p class="ops-tip">
          <b>实时备份</b>：每个文件上传完成后自动复制一份到备份目录；
          <b>定时备份</b>：每天在设定时刻增量备份全部文件 + 元数据快照（metadata.json）。
          备份位置：<code>{{ backupInfo.backup_dir || '-' }}</code>——建议在 docker-compose.yml 中把
          /data/backup 挂载到宿主机路径或 NAS（与主数据不同物理盘更安全），详见 README。
        </p>
        <el-table :data="backupInfo.runs || []" size="small">
          <el-table-column label="时间" width="150">
            <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
          </el-table-column>
          <el-table-column label="触发" width="90">
            <template #default="{ row }">{{ row.trigger === 'manual' ? '手动' : '定时' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.status === 'done'" size="small" type="success">完成</el-tag>
              <el-tag v-else-if="row.status === 'running'" size="small">进行中</el-tag>
              <el-tag v-else size="small" type="danger">失败</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="file_count" label="文件数" width="80" />
          <el-table-column label="总大小" width="100">
            <template #default="{ row }">{{ formatBytes(row.total_size) }}</template>
          </el-table-column>
          <el-table-column prop="error" label="错误" min-width="160" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span>数据完整性校验</span></template>
            <p class="ops-tip">
              重新计算全部文件的 SHA256 并与入库记录比对，用于发现磁盘静默损坏（bit rot）。
              建议每季度执行一次。
            </p>
            <el-button type="primary" :loading="verifyJob?.status === 'running'" @click="startVerify">
              {{ verifyJob?.status === 'running' ? '校验进行中…' : '启动全库校验' }}
            </el-button>
            <div v-if="verifyResult" class="verify-result">
              <el-result v-if="verifyResult.mismatched === 0 && verifyResult.missing_files === 0"
                icon="success" title="全部通过" :sub-title="`共校验 ${verifyResult.checked} 个文件`" />
              <el-result v-else icon="error" title="发现异常"
                :sub-title="`${verifyResult.mismatched} 个校验不符，${verifyResult.missing_files} 个文件缺失`" />
              <el-table v-if="verifyResult.mismatches?.length || verifyResult.missing?.length" size="small"
                :data="[...(verifyResult.mismatches || []), ...(verifyResult.missing || [])]">
                <el-table-column prop="name" label="文件" min-width="180" />
                <el-table-column label="问题" width="110">
                  <template #default="{ row }">
                    <el-tag size="small" type="danger">{{ row.actual ? '校验不符' : '文件缺失' }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header><span>项目归档导出</span></template>
            <p class="ops-tip">
              将项目（或全部）数据打包为 zip，内含文件与 metadata.json 清单（含 SHA256），供投稿材料或冷备份。
            </p>
            <div style="display: flex; gap: 8px">
              <el-select v-model="exportProjectId" clearable placeholder="全部项目" style="width: 200px">
                <el-option v-for="p in cfg.projects" :key="p.id" :label="p.code" :value="p.id" />
              </el-select>
              <el-button type="primary" @click="startExport">开始导出</el-button>
            </div>
            <el-table :data="exportJobs" size="small" style="margin-top: 12px">
              <el-table-column prop="started_at" label="时间" width="150" />
              <el-table-column label="范围" width="110">
                <template #default="{ row }">
                  {{ cfg.projectById(row.project_id)?.code || '全部' }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.status === 'done'" size="small" type="success">完成</el-tag>
                  <el-tag v-else-if="row.status === 'running'" size="small">进行中</el-tag>
                  <el-tag v-else size="small" type="danger">失败</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'done'" link type="primary" size="small"
                    @click="downloadExport(row)">下载</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </el-tab-pane>
  </el-tabs>

  <!-- 各类对话框 -->
  <el-dialog v-model="projectVisible" :title="projectForm.id ? '编辑项目' : '新建项目'" width="440px">
    <el-form label-width="70px">
      <el-form-item label="编号" required>
        <el-input v-model="projectForm.code" placeholder="如 ProjectA" />
      </el-form-item>
      <el-form-item label="名称"><el-input v-model="projectForm.name" /></el-form-item>
      <el-form-item label="描述"><el-input v-model="projectForm.description" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="projectVisible = false">取消</el-button>
      <el-button type="primary" @click="saveProject">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="categoryVisible" :title="categoryForm.id ? '编辑分类' : '新建分类'" width="440px">
    <el-form label-width="70px">
      <el-form-item label="名称" required><el-input v-model="categoryForm.name" placeholder="如 WB / PCR" /></el-form-item>
      <el-form-item label="颜色">
        <el-color-picker v-model="categoryForm.color" />
      </el-form-item>
      <el-form-item label="排序"><el-input-number v-model="categoryForm.sort_order" :min="0" /></el-form-item>
      <el-form-item label="启用"><el-switch v-model="categoryForm.is_active" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="categoryVisible = false">取消</el-button>
      <el-button type="primary" @click="saveCategory">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="fieldVisible" :title="fieldForm.id ? '编辑字段' : '添加自定义字段'" width="480px">
    <el-form label-width="90px">
      <el-form-item label="字段名" required><el-input v-model="fieldForm.label" placeholder="如 抗体 / 染色方法" /></el-form-item>
      <el-form-item label="类型">
        <el-select v-model="fieldForm.field_type" style="width: 100%">
          <el-option label="文本" value="text" />
          <el-option label="数字" value="number" />
          <el-option label="日期" value="date" />
          <el-option label="下拉选择" value="select" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="fieldForm.field_type === 'select'" label="下拉选项">
        <el-select v-model="fieldForm.select_options" multiple filterable allow-create default-first-option
          placeholder="输入后回车添加选项" style="width: 100%">
          <el-option v-for="o in fieldForm.select_options" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>
      <el-form-item label="必填"><el-switch v-model="fieldForm.is_required" /></el-form-item>
      <el-form-item label="排序"><el-input-number v-model="fieldForm.sort_order" :min="0" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="fieldVisible = false">取消</el-button>
      <el-button type="primary" @click="saveField">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="objectVisible" :title="objectForm.id ? '编辑对象' : '新建对象'" width="440px">
    <el-form label-width="70px">
      <el-form-item label="名称" required><el-input v-model="objectForm.name" placeholder="如 HEK293 / C57小鼠心脏" /></el-form-item>
      <el-form-item label="类别">
        <el-select v-model="objectForm.kind" style="width: 100%">
          <el-option label="细胞" value="cell" />
          <el-option label="动物" value="animal" />
          <el-option label="组织" value="tissue" />
          <el-option label="其他" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item label="别名"><el-input v-model="objectForm.aliases" placeholder="逗号分隔，用于检索" /></el-form-item>
      <el-form-item label="描述"><el-input v-model="objectForm.description" type="textarea" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="objectVisible = false">取消</el-button>
      <el-button type="primary" @click="saveObject">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="userVisible" :title="userForm.id ? '编辑用户' : '新建用户'" width="440px">
    <el-form label-width="80px">
      <el-form-item v-if="!userForm.id" label="用户名" required><el-input v-model="userForm.username" /></el-form-item>
      <el-form-item :label="userForm.id ? '重置密码' : '密码'" required>
        <el-input v-model="userForm.password" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
      <el-form-item label="姓名"><el-input v-model="userForm.display_name" /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="userForm.role" style="width: 100%">
          <el-option label="成员" value="member" />
          <el-option label="管理员" value="admin" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="userForm.id" label="启用"><el-switch v-model="userForm.is_active" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="userVisible = false">取消</el-button>
      <el-button type="primary" @click="saveUser">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errMsg } from '../api'
import { useConfigStore } from '../stores/config'
import { formatBytes, formatDateTime, OBJECT_KIND_LABEL, FIELD_TYPE_LABEL, tokenUrl } from '../utils'

const cfg = useConfigStore()
const tab = ref('projects')

onMounted(async () => {
  await cfg.refreshAll()
  loadUsers()
  loadVerify()
  loadBackup()
})

// ---------- 项目 ----------
const projectVisible = ref(false)
const projectForm = reactive({ id: null, code: '', name: '', description: '' })

function openProject(row) {
  Object.assign(projectForm, row ? { ...row } : { id: null, code: '', name: '', description: '' })
  projectVisible.value = true
}

async function saveProject() {
  if (!projectForm.code.trim()) return ElMessage.warning('编号必填')
  try {
    if (projectForm.id) {
      await api.put(`/projects/${projectForm.id}`, {
        code: projectForm.code, name: projectForm.name, description: projectForm.description,
      })
    } else {
      await api.post('/projects', {
        code: projectForm.code, name: projectForm.name, description: projectForm.description,
      })
    }
    ElMessage.success('已保存')
    projectVisible.value = false
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function toggleProject(row) {
  const status = row.status === 'active' ? 'archived' : 'active'
  await ElMessageBox.confirm(
    status === 'archived' ? `归档后「${row.code}」不再出现在新数据的项目下拉中。` : `恢复项目「${row.code}」？`,
    status === 'archived' ? '归档项目' : '恢复项目')
  try {
    await api.put(`/projects/${row.id}`, { status })
    ElMessage.success('已更新')
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function deleteProject(row) {
  await ElMessageBox.confirm(`删除项目「${row.code}」？仅在其下没有数据时允许。`, '删除项目', { type: 'warning' })
  try {
    await api.delete(`/projects/${row.id}`)
    ElMessage.success('已删除')
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

// ---------- 分类与自定义字段 ----------
const categoryVisible = ref(false)
const categoryForm = reactive({ id: null, name: '', color: '#409EFF', sort_order: 0, is_active: true })
const currentCategory = ref(null)
const fields = ref([])
const fieldVisible = ref(false)
const fieldForm = reactive({ id: null, label: '', field_type: 'text', select_options: [], is_required: false, sort_order: 0 })

watch(currentCategory, async (c) => { if (c) await loadFields() })

async function loadFields() {
  if (!currentCategory.value) return
  const { data } = await api.get('/custom-fields', { params: { category_id: currentCategory.value.id } })
  fields.value = data
}

function openCategory(row) {
  Object.assign(categoryForm, row ? { ...row } : { id: null, name: '', color: '#409EFF', sort_order: 0, is_active: true })
  categoryVisible.value = true
}

async function saveCategory() {
  if (!categoryForm.name.trim()) return ElMessage.warning('名称必填')
  try {
    const payload = { name: categoryForm.name, color: categoryForm.color, sort_order: categoryForm.sort_order, is_active: categoryForm.is_active }
    if (categoryForm.id) await api.put(`/categories/${categoryForm.id}`, payload)
    else await api.post('/categories', payload)
    ElMessage.success('已保存')
    categoryVisible.value = false
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function deleteCategory(row) {
  await ElMessageBox.confirm(`删除分类「${row.name}」？仅在其下没有数据时允许。`, '删除分类', { type: 'warning' })
  try {
    await api.delete(`/categories/${row.id}`)
    ElMessage.success('已删除')
    if (currentCategory.value?.id === row.id) currentCategory.value = null
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

function openField(row) {
  Object.assign(fieldForm, row
    ? { ...row, select_options: [...(row.select_options || [])] }
    : { id: null, label: '', field_type: 'text', select_options: [], is_required: false, sort_order: fields.value.length + 1 })
  fieldVisible.value = true
}

async function saveField() {
  if (!fieldForm.label.trim()) return ElMessage.warning('字段名必填')
  if (fieldForm.field_type === 'select' && !fieldForm.select_options.length) {
    return ElMessage.warning('下拉字段必须至少提供一个选项')
  }
  try {
    const payload = {
      category_id: currentCategory.value.id,
      label: fieldForm.label, field_type: fieldForm.field_type,
      select_options: fieldForm.select_options, is_required: fieldForm.is_required,
      sort_order: fieldForm.sort_order,
    }
    if (fieldForm.id) await api.put(`/custom-fields/${fieldForm.id}`, payload)
    else await api.post('/custom-fields', payload)
    ElMessage.success('已保存')
    fieldVisible.value = false
    cfg.invalidateFields(currentCategory.value.id)
    loadFields()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function deleteField(row) {
  await ElMessageBox.confirm(`删除字段「${row.label}」？已填写的历史值仍保留在数据中。`, '删除字段', { type: 'warning' })
  try {
    await api.delete(`/custom-fields/${row.id}`)
    ElMessage.success('已删除')
    cfg.invalidateFields(currentCategory.value.id)
    loadFields()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

// ---------- 对象 ----------
const objectVisible = ref(false)
const objectForm = reactive({ id: null, name: '', kind: 'cell', aliases: '', description: '' })

function openObject(row) {
  Object.assign(objectForm, row ? { ...row } : { id: null, name: '', kind: 'cell', aliases: '', description: '' })
  objectVisible.value = true
}

async function saveObject() {
  if (!objectForm.name.trim()) return ElMessage.warning('名称必填')
  try {
    if (objectForm.id) await api.put(`/objects/${objectForm.id}`, { ...objectForm })
    else await api.post('/objects', { ...objectForm })
    ElMessage.success('已保存')
    objectVisible.value = false
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function deleteObject(row) {
  await ElMessageBox.confirm(`删除对象「${row.name}」？仍有数据引用时无法删除。`, '删除对象', { type: 'warning' })
  try {
    await api.delete(`/objects/${row.id}`)
    ElMessage.success('已删除')
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

// ---------- 标签 ----------
const newTagName = ref('')

async function addTag() {
  if (!newTagName.value.trim()) return
  try {
    await api.post('/tags', { name: newTagName.value.trim() })
    newTagName.value = ''
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function deleteTag(tag) {
  try {
    await api.delete(`/tags/${tag.id}`)
    cfg.refreshAll()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

// ---------- 用户 ----------
const users = ref([])
const userVisible = ref(false)
const userForm = reactive({ id: null, username: '', password: '', display_name: '', role: 'member', is_active: true })

async function loadUsers() {
  try {
    const { data } = await api.get('/users')
    users.value = data
  } catch { /* 非管理员不会进入本页 */ }
}

function openUser(row) {
  Object.assign(userForm, row
    ? { ...row, password: '' }
    : { id: null, username: '', password: '', display_name: '', role: 'member', is_active: true })
  userVisible.value = true
}

async function saveUser() {
  if (!userForm.id && !userForm.username.trim()) return ElMessage.warning('用户名必填')
  if (!userForm.id && userForm.password.length < 6) return ElMessage.warning('密码至少 6 位')
  if (userForm.id && userForm.password && userForm.password.length < 6) return ElMessage.warning('重置密码至少 6 位')
  try {
    if (userForm.id) {
      const payload = {
        display_name: userForm.display_name, role: userForm.role, is_active: userForm.is_active,
      }
      if (userForm.password) payload.password = userForm.password
      await api.put(`/users/${userForm.id}`, payload)
    } else {
      await api.post('/users', {
        username: userForm.username, password: userForm.password,
        display_name: userForm.display_name, role: userForm.role,
      })
    }
    ElMessage.success('已保存')
    userVisible.value = false
    loadUsers()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

// ---------- 运维：备份 ----------
const backupForm = reactive({ mode: 'off', run_at: '02:00' })
const backupInfo = ref({ runs: [], backup_dir: '', setting: null })
const backupSaving = ref(false)
const backupRunning = ref(false)

async function loadBackup() {
  try {
    const { data } = await api.get('/ops/backup')
    backupInfo.value = data
    if (data.setting) {
      backupForm.mode = data.setting.mode
      backupForm.run_at = data.setting.run_at
    }
  } catch { /* ignore */ }
}

function onBackupModeChange() { /* 仅控制时间选择器显隐 */ }

async function saveBackupSetting() {
  backupSaving.value = true
  try {
    await api.put('/ops/backup', { mode: backupForm.mode, run_at: backupForm.run_at || '02:00' })
    ElMessage.success('备份设置已保存')
    loadBackup()
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    backupSaving.value = false
  }
}

async function runBackupNow() {
  backupRunning.value = true
  try {
    const { data } = await api.post('/ops/backup/run')
    // 轮询任务状态
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 2000))
      const { data: st } = await api.get(`/ops/backup/run/${data.run_id}`)
      if (st.status !== 'running') break
    }
    await loadBackup()
    const last = backupInfo.value.runs?.[0]
    if (last?.status === 'done') {
      ElMessage.success(`备份完成：${last.file_count} 个文件，共 ${formatBytes(last.total_size)}`)
    } else if (last?.status === 'error') {
      ElMessage.error(`备份失败：${last.error}`)
    }
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    backupRunning.value = false
  }
}

// ---------- 运维：校验 ----------
const verifyJob = ref(null)
const verifyResult = ref(null)
const exportProjectId = ref(null)
const exportJobs = ref([])

async function loadVerify() {
  try {
    const { data } = await api.get('/ops/verify')
    verifyJob.value = data
    verifyResult.value = data.result
  } catch { /* ignore */ }
}

async function startVerify() {
  try {
    await api.post('/ops/verify')
    ElMessage.success('校验已启动，稍后刷新查看结果')
    pollVerify()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function pollVerify() {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    const { data } = await api.get('/ops/verify')
    verifyJob.value = data
    verifyResult.value = data.result
    if (data.status === 'done' || data.status === 'error') break
  }
}

async function startExport() {
  try {
    await api.post('/ops/export', { project_id: exportProjectId.value ?? null })
    ElMessage.success('导出任务已启动')
    pollExports()
  } catch (e) { ElMessage.error(errMsg(e)) }
}

async function pollExports() {
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 2000))
    const { data } = await api.get('/ops/export')
    exportJobs.value = data
    if (!data.some((j) => j.status === 'running')) break
  }
}

function downloadExport(job) {
  window.open(tokenUrl(`/api/ops/export/${job.id}/download`), '_blank')
}
</script>

<style scoped>
.pane-head { display: flex; align-items: center; margin-bottom: 10px; min-height: 32px; }
.cat-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
.dim { color: #909399; font-size: 13px; }
.tag-wall { padding: 8px 0; }
.ops-card { margin-bottom: 14px; }
.ops-tip { color: #909399; font-size: 13px; line-height: 1.7; }
.ops-tip code { background: #f0f2f5; padding: 1px 6px; border-radius: 4px; color: #476582; }
.verify-result { margin-top: 14px; }
</style>
