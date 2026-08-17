<template>
  <div class="upload-page">
    <el-row :gutter="16">
      <!-- 左：文件区 -->
      <el-col :span="12">
        <el-card class="page-card">
          <template #header>
            <div class="card-header">
              <span>① 选择文件</span>
              <el-radio-group v-model="mode" size="small">
                <el-radio-button value="flat">单批模式</el-radio-button>
                <el-radio-button value="group">分组模式</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <!-- ===== 单批模式 ===== -->
          <template v-if="mode === 'flat'">
            <el-upload drag multiple :auto-upload="false" :show-file-list="false" :on-change="onFileAdd">
              <el-icon :size="42" color="#909399"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
              <template #tip>
                <div class="el-upload__tip">
                  支持任意格式；大文件自动分片上传，相同内容秒传
                </div>
              </template>
            </el-upload>
            <div class="file-queue">
              <div v-for="(f, idx) in files" :key="f.uid" class="file-row">
                <el-icon class="file-icon"><Document /></el-icon>
                <div class="file-info">
                  <div class="file-name" :title="f.name">{{ f.name }}</div>
                  <el-progress v-if="f.status !== 'waiting'" :percentage="f.progress"
                    :status="progressStatus(f)" :stroke-width="6" />
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
          </template>

          <!-- ===== 分组模式：原始文件 + 派生文件成组，元数据填一次自动同步 ===== -->
          <template v-else>
            <div
              class="group-dropzone" :class="{ dragging }"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="onGroupDrop"
            >
              <el-icon :size="36" color="#909399"><FolderAdd /></el-icon>
              <div class="el-upload__text">拖入<b>文件夹</b>或文件到此处</div>
              <div class="dropzone-btns">
                <el-button size="small" @click="$refs.dirInput.click()">选择文件夹</el-button>
                <el-button size="small" @click="$refs.fileInput.click()">选择文件</el-button>
              </div>
              <div class="el-upload__tip">
                每个子文件夹识别为一个组（组内默认<b>最大的文件</b>为原始文件，其余为派生文件）；
                散放文件各自成组
              </div>
              <input ref="dirInput" type="file" webkitdirectory multiple style="display: none" @change="onDirPick" />
              <input ref="fileInput" type="file" multiple style="display: none" @change="onFilesPick" />
            </div>

            <div class="group-queue">
              <div v-for="g in groups" :key="g.id" class="group-card">
                <div class="group-head">
                  <el-icon color="#409eff"><Folder /></el-icon>
                  <span class="group-name" :title="g.name">{{ g.name }}</span>
                  <el-tag size="small" type="info" effect="plain">{{ g.files.length }} 个文件</el-tag>
                  <span class="flex-grow" />
                  <el-input v-model="g.derive_note" size="small" class="group-note"
                    placeholder="派生说明（可选，如：条带截取）" />
                  <el-icon class="remove" @click="removeGroup(g.id)"><CircleClose /></el-icon>
                </div>
                <div v-for="f in g.files" :key="f.uid" class="file-row">
                  <el-radio :model-value="g.primaryUid" :value="f.uid" @change="g.primaryUid = f.uid">
                    <span class="primary-label">原始</span>
                  </el-radio>
                  <el-icon class="file-icon"><Document /></el-icon>
                  <div class="file-info">
                    <div class="file-name" :title="f.name">
                      {{ f.relPath || f.name }}
                      <el-tag v-if="g.primaryUid === f.uid" size="small" type="primary" style="margin-left: 4px">原始文件</el-tag>
                    </div>
                    <el-progress v-if="f.status !== 'waiting'" :percentage="f.progress"
                      :status="progressStatus(f)" :stroke-width="6" />
                  </div>
                  <div class="file-meta">
                    <span class="size">{{ formatBytes(f.size) }}</span>
                    <el-tag v-if="f.status === 'instant'" size="small" type="success">秒传</el-tag>
                    <el-tag v-else-if="f.status === 'done'" size="small" type="success">完成</el-tag>
                    <el-tag v-else-if="f.status === 'error'" size="small" type="danger">失败</el-tag>
                    <el-icon v-if="g.files.length > 1" class="remove"
                      @click="removeGroupFile(g, f)"><CircleClose /></el-icon>
                  </div>
                </div>
              </div>
              <el-empty v-if="!groups.length" description="尚未选择文件夹或文件" :image-size="70" />
            </div>
          </template>
        </el-card>
      </el-col>

      <!-- 右：元数据表单 -->
      <el-col :span="12">
        <el-card class="page-card">
          <template #header>
            <span>{{ mode === 'group' ? '② 填写元数据（只需给每组的原始文件填一次，派生文件自动同步）' : '② 填写元数据（对本次全部文件生效）' }}</span>
          </template>

          <el-form label-width="92px" label-position="right">
            <template v-if="mode === 'flat'">
              <el-form-item label="数据类型">
                <el-radio-group v-model="form.kind">
                  <el-radio-button value="raw">原始数据</el-radio-button>
                  <el-radio-button value="derived">派生数据</el-radio-button>
                  <el-radio-button value="backup">备份文件</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <template v-if="form.kind === 'derived'">
                <el-form-item label="父文件" required>
                  <el-select v-model="form.parent_record_id" filterable remote :remote-method="searchParents"
                    :loading="parentLoading" placeholder="输入文件名 / 标题搜索原始数据" style="width: 100%">
                    <el-option v-for="p in parentOptions" :key="p.id"
                      :label="`#${p.id} ${p.original_name}${p.title ? ' · ' + p.title : ''}`" :value="p.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="派生说明">
                  <el-input v-model="form.derive_note" placeholder="如：GAPDH 条带截取 / 200x 放大" />
                </el-form-item>
              </template>
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

            <MetaFields v-model="form.custom_values" :fields="fields" />

            <el-form-item label="实验对象">
              <el-select v-model="form.object_name" filterable clearable allow-create default-first-option
                placeholder="什么细胞 / 动物 / 组织，可输入新建" style="width: 100%">
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
      <div class="hint">{{ submitHint }}</div>
      <el-button type="primary" size="large" :loading="submitting" :disabled="!canSubmit" @click="submitAll">
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

const mode = ref('flat')
const files = ref([]) // 单批模式
const groups = ref([]) // 分组模式 [{id, name, primaryUid, derive_note, files:[item]}]
const dragging = ref(false)
const submitting = ref(false)
let groupSeq = 0

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
    mode.value = 'flat'
    form.kind = 'derived'
    form.parent_record_id = Number(route.query.parent)
    try {
      const { data } = await api.get(`/records/${route.query.parent}`)
      parentOptions.value = [data.record]
    } catch { /* ignore */ }
  }
})

// 分类变化时重新加载该分类的自定义字段（force 刷新，保证最近使用值最新）
watch(() => form.category_id, () => loadFields(true), { immediate: true })

async function loadFields(force = false) {
  fields.value = form.category_id ? await cfg.loadFields(form.category_id, { force }) : []
}

// ---------- 文件选择 ----------

function makeItem(fileObj) {
  // fileObj 必须是原生 File/Blob（依赖 slice/arrayBuffer），relPath 为附加属性
  return {
    uid: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name: fileObj.name,
    size: fileObj.size,
    raw: fileObj,
    relPath: fileObj.relPath || '',
    status: 'waiting',
    progress: 0,
  }
}

function onFileAdd(file) {
  files.value.push(makeItem(file.raw))
}

// ---------- 分组模式：文件夹读取 ----------

function addAsGroups(fileLikes) {
  // 按相对路径第一级目录分组；无目录的散文件各自成组
  const byFolder = new Map()
  for (const fl of fileLikes) {
    const rel = fl.relPath || fl.name
    const segs = rel.split('/')
    const folder = segs.length > 1 ? segs[0] : ''
    if (!byFolder.has(folder)) byFolder.set(folder, [])
    byFolder.get(folder).push(fl)
  }
  for (const [folder, fls] of byFolder) {
    const items = fls.map(makeItem)
    // 默认原始文件 = 组内最大文件（如 WB 的 scn 原图）
    const primary = items.reduce((a, b) => (b.size > a.size ? b : a), items[0])
    groups.value.push({
      id: ++groupSeq,
      name: folder || fls[0].name,
      primaryUid: primary.uid,
      derive_note: '',
      files: items,
    })
  }
}

function onDirPick(e) {
  const fls = [...e.target.files]
  for (const f of fls) f.relPath = f.webkitRelativePath || f.name
  addAsGroups(fls)
  e.target.value = ''
}

function onFilesPick(e) {
  const fls = [...e.target.files]
  for (const f of fls) f.relPath = f.name
  addAsGroups(fls)
  e.target.value = ''
}

function onGroupDrop(e) {
  dragging.value = false
  const entries = [...(e.dataTransfer.items || [])]
    .map((it) => it.webkitGetAsEntry?.())
    .filter(Boolean)
  if (entries.length) {
    const out = []
    Promise.all(entries.map((en) => walkEntry(en, '', out))).then(() => addAsGroups(out))
  } else {
    const fls = [...e.dataTransfer.files]
    for (const f of fls) f.relPath = f.name
    addAsGroups(fls)
  }
}

function walkEntry(entry, prefix, out) {
  return new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((f) => {
        f.relPath = prefix + f.name
        out.push(f)
        resolve()
      }, resolve)
    } else if (entry.isDirectory) {
      const reader = entry.createReader()
      const readBatch = () => reader.readEntries(async (children) => {
        if (!children.length) return resolve()
        for (const child of children) await walkEntry(child, prefix + entry.name + '/', out)
        readBatch() // 目录条目超过 100 个时需反复读取
      }, resolve)
      readBatch()
    } else {
      resolve()
    }
  })
}

function removeGroup(id) {
  groups.value = groups.value.filter((g) => g.id !== id)
}

function removeGroupFile(g, f) {
  g.files = g.files.filter((x) => x.uid !== f.uid)
  if (g.primaryUid === f.uid && g.files.length) g.primaryUid = g.files[0].uid
}

// ---------- 上传核心 ----------

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
  if (mode.value === 'flat' && form.kind === 'derived' && !form.parent_record_id) {
    return '派生数据必须选择父文件'
  }
  for (const f of fields.value) {
    const v = form.custom_values[f.field_key]
    if (f.is_required && (v === undefined || v === null || v === '')) return `必填字段「${f.label}」未填写`
  }
  for (const g of groups.value) {
    if (g.files.length >= 2 && !g.files.some((f) => f.uid === g.primaryUid)) return `组「${g.name}」未指定原始文件`
  }
  return null
}

const canSubmit = computed(() =>
  mode.value === 'flat' ? files.value.some((f) => f.status !== 'done' && f.status !== 'instant') : groups.value.length > 0)

const submitHint = computed(() => {
  if (mode.value === 'flat') {
    return `已选 ${files.value.length} 个文件`
      + (form.kind === 'derived' ? '，将作为派生数据关联到父文件' : '')
  }
  const n = groups.value.length
  const raw = groups.value.filter((g) => g.files.length > 1).length
  return `共 ${n} 组（${raw} 组含原始+派生），元数据填写一次自动同步`
})

async function resolveRelations() {
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
  return { objectId, tagIds }
}

async function submitAll() {
  const err = validate()
  if (err) return ElMessage.warning(err)
  submitting.value = true
  try {
    const { objectId, tagIds } = await resolveRelations()
    const baseMeta = {
      project_id: form.project_id === '' ? null : form.project_id,
      category_id: form.category_id === '' ? null : form.category_id,
      object_id: objectId,
      recorded_date: form.recorded_date,
      title: form.title,
      note: form.note,
      custom_values: form.custom_values,
      tag_ids: tagIds,
    }

    if (mode.value === 'flat') {
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
      const { data } = await api.post('/records', {
        ...baseMeta,
        file_ids: fileIds,
        kind: form.kind,
        parent_record_id: form.kind === 'derived' ? form.parent_record_id : null,
        derive_note: form.derive_note,
      })
      await finishMessage(data)
      return
    }

    // 分组模式：每组先建原始记录，派生文件挂到它下面并自动继承元数据
    let totalCreated = 0
    const warnings = []
    for (const g of groups.value) {
      const primary = g.files.find((f) => f.uid === g.primaryUid) || g.files[0]
      const others = g.files.filter((f) => f !== primary)

      primary.status = 'uploading'
      const primaryFileId = await uploadOne(primary)
      const { data: rawResp } = await api.post('/records', {
        ...baseMeta, file_ids: [primaryFileId], kind: 'raw',
      })
      totalCreated += rawResp.items.length
      warnings.push(...(rawResp.warnings || []))

      if (others.length) {
        const derivedIds = []
        for (const f of others) {
          f.status = 'uploading'
          try {
            derivedIds.push(await uploadOne(f))
          } catch (e) {
            f.status = 'error'
            throw new Error(`${f.name} 上传失败：${errMsg(e)}`)
          }
        }
        const { data: derResp } = await api.post('/records', {
          file_ids: derivedIds,
          kind: 'derived',
          parent_record_id: rawResp.items[0].id,
          derive_note: g.derive_note || form.derive_note,
        })
        totalCreated += derResp.items.length
        warnings.push(...(derResp.warnings || []))
      }
    }
    await finishMessage({ items: new Array(totalCreated), warnings: [...new Set(warnings)] }, totalCreated)
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    submitting.value = false
  }
}

async function finishMessage(data, countOverride) {
  const n = countOverride ?? data.items.length
  let msg = `成功入库 ${n} 条数据`
  if (data.warnings?.length) msg += '\n' + data.warnings.join('\n')
  await ElMessageBox.alert(msg, '上传完成', {
    type: data.warnings?.length ? 'warning' : 'success',
    confirmButtonText: '去查看',
    cancelButtonText: '留在本页',
    showCancelButton: true,
  }).then(() => router.push('/browse')).catch(() => {})
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.file-queue, .group-queue { margin-top: 12px; max-height: 430px; overflow: auto; }
.file-row {
  display: flex; align-items: center; gap: 10px; padding: 6px 10px;
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
.primary-label { font-size: 12px; }

.group-dropzone {
  border: 1px dashed #c0c4cc; border-radius: 8px; padding: 22px 10px; text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  transition: border-color .2s, background .2s;
}
.group-dropzone.dragging { border-color: #409eff; background: #ecf5ff; }
.dropzone-btns { display: flex; gap: 8px; }
.group-card { border: 1px solid #ebeef5; border-radius: 8px; padding: 8px 10px; margin-bottom: 10px; }
.group-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.group-name { font-weight: 600; font-size: 13px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.flex-grow { flex: 1; }
.group-note { width: 220px; }
.submit-bar {
  position: sticky; bottom: 0; background: #f5f7fa; padding: 12px 4px;
  display: flex; justify-content: space-between; align-items: center;
}
.hint { color: #606266; font-size: 14px; }
</style>
