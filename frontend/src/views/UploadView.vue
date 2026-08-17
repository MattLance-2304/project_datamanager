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
                <div class="el-upload__tip">支持任意格式；大文件自动分片上传，相同内容秒传</div>
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

          <!-- ===== 分组模式：未分组池 + 组块拖拽板 ===== -->
          <template v-else>
            <div class="group-toolbar">
              <el-button size="small" type="primary" @click="$refs.dirInput.click()">
                <el-icon><FolderAdd /></el-icon>选择文件夹
              </el-button>
              <el-button size="small" @click="$refs.fileInput.click()">选择文件</el-button>
              <span class="flex-grow" />
              <el-tooltip content="开启后：拖入的文件夹按一级子文件夹自动成一个组；关闭后：所有文件进入上方未分组池，由你手动拖入各组织" placement="top">
                <el-switch v-model="autoGroup" active-text="按子文件夹自动分组" size="small" />
              </el-tooltip>
            </div>

            <!-- 未分组池 -->
            <div
              class="pool" :class="{ 'drop-hot': poolHot }"
              @dragenter.prevent="poolEnter($event)"
              @dragover.prevent="poolHot = true"
              @dragleave="poolLeave($event)"
              @drop.prevent="onDropZone($event, { target: 'pool' })"
            >
              <div class="pool-title">
                <el-icon><Box /></el-icon> 未分组文件池
                <span class="dim">（把下面的文件/文件夹拖到任意组块中即成组；上传时留在这里的文件将各自作为独立原始数据）</span>
              </div>
              <div class="pool-chips">
                <div v-for="f in pool" :key="f.uid" class="chip" draggable="true"
                  @dragstart="startItemDrag($event, { pool: true }, f)" @dragend="endItemDrag">
                  <span class="chip-name" :title="f.relPath || f.name">{{ f.relPath || f.name }}</span>
                  <span class="chip-size">{{ formatBytes(f.size) }}</span>
                  <el-icon class="remove" @click="pool = pool.filter((x) => x.uid !== f.uid)"><CircleClose /></el-icon>
                </div>
                <div v-if="!pool.length" class="pool-empty">拖入文件 / 文件夹，或用上方按钮选择</div>
              </div>
            </div>

            <!-- 组块板 -->
            <div class="board">
              <div
                v-for="g in groups" :key="g.id"
                class="group-block" :class="{ 'drop-hot': g._hot, uploading: g._busy }"
                @dragenter.prevent="groupEnter($event, g)"
                @dragover.prevent="g._hot = true"
                @dragleave="groupLeave($event, g)"
                @drop.prevent="onDropZone($event, { target: 'group', group: g })"
              >
                <div class="group-head">
                  <el-icon color="#409eff" :size="18"><Collection /></el-icon>
                  <input v-model="g.name" class="group-name-input" placeholder="组名" />
                  <el-tag size="small" type="info" effect="plain">{{ g.files.length }} 文件</el-tag>
                  <span class="flex-grow" />
                  <el-icon class="remove" title="删除整组" @click="removeGroup(g.id)"><CircleClose /></el-icon>
                </div>
                <div v-if="g.files.length >= 2" class="group-note-row">
                  <el-input v-model="g.derive_note" size="small" placeholder="派生说明（如：条带截取 / 200x 放大）" />
                </div>
                <div class="group-files">
                  <div v-for="f in g.files" :key="f.uid" class="file-row" draggable="true"
                    @dragstart="startItemDrag($event, { group: g }, f)" @dragend="endItemDrag">
                    <el-radio :model-value="g.primaryUid" :value="f.uid" @change="g.primaryUid = f.uid">
                      原始
                    </el-radio>
                    <el-icon class="file-icon"><Document /></el-icon>
                    <div class="file-info">
                      <div class="file-name" :title="f.relPath || f.name">
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
                      <el-icon class="remove" title="移出（拖到池子也可）"
                        @click="moveFile({ group: g }, f, { pool: true })"><Bottom /></el-icon>
                    </div>
                  </div>
                  <div v-if="!g.files.length" class="group-empty">空组——把文件拖进来</div>
                </div>
              </div>

              <!-- 新建组块：拖文件到此处 = 新建组并放入 -->
              <div
                class="group-block new-block"
                @dragenter.prevent="newHot = true" @dragover.prevent="newHot = true"
                @dragleave="newLeave($event)" @drop.prevent="onDropZone($event, { target: 'new' })"
                @click="createGroup()"
              >
                <el-icon :size="26" color="#409eff"><CirclePlus /></el-icon>
                <div>新建组</div>
                <div class="dim" style="font-size: 12px">拖文件/文件夹到此处可快速建组</div>
              </div>
            </div>

            <input ref="dirInput" type="file" webkitdirectory multiple style="display: none" @change="onDirPick" />
            <input ref="fileInput" type="file" multiple style="display: none" @change="onFilesPick" />
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
const pool = ref([]) // 分组模式：未分组文件池
const groups = ref([]) // 分组模式：[{id, name, primaryUid, derive_note, files, _hot, _busy}]
const autoGroup = ref(true)
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

// 内部拖动状态（文件条目 → 组块/池子）
const dragItem = ref(null)
const poolHot = ref(false)
const newHot = ref(false)

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

// ---------- 文件条目 ----------

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

// ---------- 外部文件导入（文件夹递归读取） ----------

function onDirPick(e) {
  importFiles([...e.target.files].map((f) => {
    f.relPath = f.webkitRelativePath || f.name
    return f
  }))
  e.target.value = ''
}

function onFilesPick(e) {
  importFiles([...e.target.files].map((f) => {
    f.relPath = f.name
    return f
  }))
  e.target.value = ''
}

/** 外部 drop / 选择器导入统一入口。fls 为带 relPath 的原生 File 列表。 */
function importFiles(fls) {
  if (!fls.length) return
  if (autoGroup.value) {
    // 按一级子文件夹自动成组；散文件进池子
    const byFolder = new Map()
    const loose = []
    for (const fl of fls) {
      const rel = fl.relPath || fl.name
      const segs = rel.split('/')
      if (segs.length > 1) {
        const folder = segs[0]
        if (!byFolder.has(folder)) byFolder.set(folder, [])
        byFolder.get(folder).push(fl)
      } else {
        loose.push(fl)
      }
    }
    for (const [folder, list] of byFolder) {
      const g = createGroup(folder)
      g.files = list.map(makeItem)
      g.primaryUid = defaultPrimary(g).uid
    }
    if (loose.length) pool.value.push(...loose.map(makeItem))
    if (loose.length && !byFolder.size) {
      ElMessage.info(`${loose.length} 个散文件已放入未分组池，可拖入组块编组`)
    }
  } else {
    pool.value.push(...fls.map(makeItem))
  }
}

/** 统一 drop 处理：内部拖动 → 移动文件；外部拖入 → 导入（可指定落入的组块）。 */
function onDropZone(e, { target, group }) {
  clearHot()
  if (dragItem.value) {
    const item = dragItem.value
    dragItem.value = null
    if (target === 'pool') {
      moveFile(item, item.f, { pool: true })
    } else if (target === 'group') {
      if (item.group?.id === group.id && item.f.uid !== group.primaryUid) return // 原地不动
      moveFile(item, item.f, { group })
    } else if (target === 'new') {
      const g = createGroup()
      moveFile(item, item.f, { group: g })
    }
    return
  }
  // 外部文件/文件夹
  const entries = [...(e.dataTransfer.items || [])]
    .map((it) => it.webkitGetAsEntry?.())
    .filter(Boolean)
  if (entries.length) {
    const out = []
    Promise.all(entries.map((en) => walkEntry(en, '', out))).then(() => landExternals(out, { target, group }))
  } else if (e.dataTransfer.files?.length) {
    const fls = [...e.dataTransfer.files].map((f) => {
      f.relPath = f.name
      return f
    })
    landExternals(fls, { target, group })
  }
}

/** 外部文件落地：拖到具体组块 → 全部进该组；拖到池子/新建块 → 走自动分组或进池。 */
function landExternals(fls, { target, group }) {
  if (!fls.length) return
  if (target === 'group') {
    const items = fls.map(makeItem)
    group.files.push(...items)
    if (!group.files.some((f) => f.uid === group.primaryUid)) {
      group.primaryUid = defaultPrimary(group).uid
    }
    return
  }
  if (target === 'new') {
    const g = createGroup()
    g.files = fls.map(makeItem)
    g.primaryUid = defaultPrimary(g).uid
    return
  }
  importFiles(fls) // 落到池子：按自动分组开关处理
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

// ---------- 组块与内部拖动 ----------

function createGroup(name = '') {
  const g = reactive({
    id: ++groupSeq,
    name: name || `组 ${groupSeq}`,
    primaryUid: '',
    derive_note: '',
    recordId: null, // 原始记录建好后暂存，供部分失败重试时复用
    files: [],
    _hot: false,
    _busy: false,
  })
  groups.value.push(g)
  return g
}

function defaultPrimary(g) {
  // 组内最大文件默认为原始文件（如 WB 的 scn 原图）
  return g.files.reduce((a, b) => (b.size > a.size ? b : a), g.files[0])
}

function startItemDrag(e, location, f) {
  dragItem.value = { ...location, f }
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', f.name) // Firefox 需要 setData 才能启动拖拽
}

function endItemDrag() {
  dragItem.value = null
  clearHot()
}

/** 把文件 f 从 from 移动到 to（组或池子） */
function moveFile(from, f, to) {
  // 从源移除
  if (from.pool) {
    pool.value = pool.value.filter((x) => x.uid !== f.uid)
  } else if (from.group) {
    from.group.files = from.group.files.filter((x) => x.uid !== f.uid)
    if (from.group.primaryUid === f.uid && from.group.files.length) {
      from.group.primaryUid = defaultPrimary(from.group).uid
    }
  }
  // 放入目标
  if (to.pool) {
    pool.value.push(f)
  } else if (to.group) {
    to.group.files.push(f)
    if (!to.group.primaryUid || !to.group.files.some((x) => x.uid === to.group.primaryUid)) {
      to.group.primaryUid = defaultPrimary(to.group).uid
    }
  }
}

function removeGroup(id) {
  const g = groups.value.find((x) => x.id === id)
  if (g && g.files.length) {
    pool.value.push(...g.files) // 组删除时文件退回池子，不丢失
  }
  groups.value = groups.value.filter((x) => x.id !== id)
}

// ---------- 拖拽高亮（enter/leave 穿透子元素抖动处理） ----------

function containsRelated(e) {
  const rt = e.relatedTarget
  return rt && e.currentTarget && e.currentTarget.contains(rt)
}

function poolEnter(e) { if (!containsRelated(e)) poolHot.value = true }
function poolLeave(e) { if (!containsRelated(e)) poolHot.value = false }
function groupEnter(e, g) { if (!containsRelated(e)) g._hot = true }
function groupLeave(e, g) { if (!containsRelated(e)) g._hot = false }
function newLeave(e) { if (!containsRelated(e)) newHot.value = false }

function clearHot() {
  poolHot.value = false
  newHot.value = false
  groups.value.forEach((g) => (g._hot = false))
}

// ---------- 上传 ----------

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
  if (f.fileId) return f.fileId // 已上传过（秒传或上次成功），直接复用
  if (f.size <= 512 * 1024 * 1024) {
    try {
      const hash = await sha256File(f)
      const { data } = await api.post('/uploads/check-hash', { sha256: hash })
      if (data.exists) {
        f.status = 'instant'
        f.progress = 100
        f.fileId = data.file_id
        return f.fileId
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
  f.fileId = done.file_id
  return f.fileId
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

const canSubmit = computed(() => {
  if (mode.value === 'flat') return files.value.some((f) => f.status !== 'done' && f.status !== 'instant')
  const inGroups = groups.value.reduce((n, g) => n + g.files.filter((f) => f.status === 'waiting').length, 0)
  return inGroups + pool.value.filter((f) => f.status === 'waiting').length > 0
})

const submitHint = computed(() => {
  if (mode.value === 'flat') {
    return `已选 ${files.value.length} 个文件` + (form.kind === 'derived' ? '，将作为派生数据关联到父文件' : '')
  }
  const multi = groups.value.filter((g) => g.files.length > 1).length
  return `${groups.value.length} 个组（${multi} 组含原始+派生），池中 ${pool.value.length} 个散文件将各自独立入库`
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

/** 上传一个组：先原始文件建记录，派生文件挂到它名下自动继承元数据。 */
async function submitGroup(g, baseMeta) {
  const primary = g.files.find((f) => f.uid === g.primaryUid) || g.files[0]
  const others = g.files.filter((f) => f !== primary)
  const warnings = []
  let created = 0

  let parentRecordId = g.recordId || null
  if (!parentRecordId) {
    primary.status = primary.fileId ? primary.status : 'uploading'
    const primaryFileId = await uploadOne(primary)
    const { data: rawResp } = await api.post('/records', {
      ...baseMeta, file_ids: [primaryFileId], kind: 'raw',
    })
    parentRecordId = rawResp.items[0].id
    g.recordId = parentRecordId // 记住：部分失败重试时不重复建原始记录
    created += rawResp.items.length
    warnings.push(...(rawResp.warnings || []))
  }

  const pendingOthers = others.filter((f) => !f.fileId)
  if (pendingOthers.length) {
    const derivedIds = []
    for (const f of pendingOthers) {
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
      parent_record_id: parentRecordId,
      derive_note: g.derive_note || form.derive_note,
    })
    created += derResp.items.length
    warnings.push(...(derResp.warnings || []))
  }
  return { created, warnings }
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
      await finishMessage({ items: data.items, warnings: data.warnings })
      return
    }

    // 分组模式：先传各编组（原始+派生），池中散文件各自作为独立原始数据
    let total = 0
    const warnings = []
    for (const g of groups.value) {
      if (!g.files.some((f) => f.status === 'waiting')) continue
      g._busy = true
      try {
        const r = await submitGroup(g, baseMeta)
        total += r.created
        warnings.push(...r.warnings)
      } finally {
        g._busy = false
      }
    }
    const loose = pool.value.filter((f) => f.status === 'waiting')
    if (loose.length) {
      const ids = []
      for (const f of loose) {
        f.status = 'uploading'
        try {
          ids.push(await uploadOne(f))
        } catch (e) {
          f.status = 'error'
          throw new Error(`${f.name} 上传失败：${errMsg(e)}`)
        }
      }
      const { data } = await api.post('/records', { ...baseMeta, file_ids: ids, kind: 'raw' })
      total += data.items.length
      warnings.push(...(data.warnings || []))
    }
    await finishMessage({ items: new Array(total), warnings: [...new Set(warnings)] }, total)
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
.file-queue { margin-top: 12px; max-height: 430px; overflow: auto; }
.file-row {
  display: flex; align-items: center; gap: 10px; padding: 6px 10px;
  border: 1px solid #ebeef5; border-radius: 6px; margin-bottom: 8px;
  background: #fff; cursor: grab;
}
.file-row:active { cursor: grabbing; }
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
.dim { color: #909399; }
.flex-grow { flex: 1; }

.group-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }

.pool {
  border: 1px dashed #c0c4cc; border-radius: 10px; padding: 8px 10px; margin-bottom: 12px;
  background: #fafbfc; transition: border-color .15s, background .15s;
}
.pool.drop-hot { border-color: #409eff; background: #ecf5ff; }
.pool-title { font-size: 13px; font-weight: 600; color: #606266; display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.pool-title .dim { font-weight: 400; font-size: 12px; }
.pool-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  display: inline-flex; align-items: center; gap: 6px; max-width: 260px;
  border: 1px solid #dcdfe6; border-radius: 14px; padding: 2px 10px; font-size: 12px;
  background: #fff; cursor: grab; user-select: none;
}
.chip:active { cursor: grabbing; }
.chip-name { color: #303133; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chip-size { color: #909399; flex-shrink: 0; }
.pool-empty, .group-empty { color: #c0c4cc; font-size: 12px; padding: 8px 2px; }

.board {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px;
  max-height: 430px; overflow: auto; padding: 2px;
}
.group-block {
  border: 1.5px solid #d9e4f1; border-radius: 14px; padding: 8px 10px; background: #fff;
  transition: border-color .15s, box-shadow .15s;
}
.group-block.drop-hot { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64, 158, 255, .15); background: #f5faff; }
.group-block.uploading { opacity: .85; }
.group-head { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
.group-name-input {
  border: none; outline: none; font-weight: 600; font-size: 13px; color: #303133;
  width: 110px; border-bottom: 1px dashed #dcdfe6; background: transparent;
}
.group-name-input:focus { border-bottom-color: #409eff; }
.group-note-row { margin-bottom: 6px; }
.new-block {
  border-style: dashed; display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 4px; color: #606266; font-size: 13px; min-height: 120px; cursor: pointer;
}
.new-block.drop-hot { border-color: #409eff; background: #f5faff; color: #409eff; }
.submit-bar {
  position: sticky; bottom: 0; background: #f5f7fa; padding: 12px 4px;
  display: flex; justify-content: space-between; align-items: center;
}
.hint { color: #606266; font-size: 14px; }
</style>
