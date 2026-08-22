<template>
  <div class="ij-page">
    <div class="ij-toolbar">
      <el-button link @click="router.back()"><el-icon><ArrowLeft /></el-icon>返回</el-button>
      <div class="ij-file" :title="record?.original_name">
        <el-icon><Picture /></el-icon>
        {{ record?.original_name || '加载中…' }}
      </div>
      <span class="flex-grow" />
      <el-button :loading="pushing" @click="pushImageToIJ">
        <el-icon><Promotion /></el-icon>把图像送入 ImageJ
      </el-button>
      <el-button @click="downloadImage"><el-icon><Download /></el-icon>下载图像</el-button>
      <el-button type="primary" @click="uploadResult">
        <el-icon><Upload /></el-icon>上传处理结果（存为派生文件）
      </el-button>
    </div>

    <el-alert type="info" :closable="false" class="ij-tip">
      <template #title>
        浏览器内运行的完整 ImageJ（首次加载需编译 Java 运行时，约 10~60 秒，请耐心等待）。
        处理完成后在 ImageJ 中 <b>File → Save</b> 保存到本机，再点右上角
        <b>「上传处理结果」</b>，文件会作为当前图像的派生数据入库并自动建立谱系。
        图像未自动出现时：点击「把图像送入 ImageJ」，或直接把下载的文件拖进 ImageJ 窗口。
      </template>
    </el-alert>

    <div class="ij-frame-wrap">
      <iframe
        ref="ijFrame" src="/imagej/index.html" class="ij-frame"
        allow="clipboard-read; clipboard-write" @load="onFrameLoad"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errMsg } from '../api'
import { tokenUrl } from '../utils'

const route = useRoute()
const router = useRouter()
const record = ref(null)
const ijFrame = ref(null)
const frameReady = ref(false)
const pushing = ref(false)

onMounted(async () => {
  try {
    const { data } = await api.get(`/records/${route.params.id}`)
    record.value = data.record
  } catch (e) {
    ElMessage.error(errMsg(e))
    router.push('/browse')
  }
})

function downloadUrl() {
  return tokenUrl(`/api/records/${route.params.id}/download`)
}

function downloadImage() {
  window.open(downloadUrl(), '_blank')
}

function onFrameLoad() {
  frameReady.value = true
  // ImageJ 前端就绪后（CheerpJ 运行时还要继续初始化）延迟尝试送图
  setTimeout(pushImageToIJ, 15000)
}

async function pushImageToIJ() {
  // 把图像以“拖放”的方式注入同源 iframe 中的 ImageJ；失败不影响手动操作
  if (!frameReady.value || !ijFrame.value) return
  pushing.value = true
  try {
    const resp = await fetch(downloadUrl())
    if (!resp.ok) throw new Error('下载失败')
    const blob = await resp.blob()
    const name = record.value?.original_name || 'image'
    const win = ijFrame.value.contentWindow
    const dt = new win.DataTransfer()
    dt.items.add(new File([blob], name, { type: blob.type }))
    for (const type of ['dragenter', 'dragover', 'drop']) {
      win.document.dispatchEvent(new win.DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt }))
    }
    ElMessage.success('已尝试注入 ImageJ，若窗口中未出现图像，请直接拖入或用 File → Open')
  } catch (e) {
    ElMessage.warning('自动送图未成功：请点击「下载图像」后，把文件拖入 ImageJ 窗口')
  } finally {
    pushing.value = false
  }
}

function uploadResult() {
  router.push({ path: '/upload', query: { parent: route.params.id, derive: 1 } })
}
</script>

<style scoped>
.ij-page { height: calc(100vh - 90px); display: flex; flex-direction: column; }
.ij-toolbar {
  display: flex; align-items: center; gap: 10px; padding: 8px 0; flex-wrap: wrap;
}
.ij-file {
  display: flex; align-items: center; gap: 6px; font-weight: 600; color: #303133;
  max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.flex-grow { flex: 1; }
.ij-tip { margin-bottom: 8px; }
.ij-frame-wrap {
  flex: 1; border: 1px solid #dcdfe6; border-radius: 8px; overflow: hidden; background: #fff;
}
.ij-frame { width: 100%; height: 100%; border: none; display: block; }
</style>
