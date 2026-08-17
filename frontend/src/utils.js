export function formatBytes(n) {
  if (n == null) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
}

export function formatDateTime(iso) {
  if (!iso) return '-'
  const s = String(iso).replace('T', ' ')
  return s.length >= 16 ? s.slice(0, 16) : s
}

export function formatDate(iso) {
  if (!iso) return '-'
  return String(iso).slice(0, 10)
}

export function tokenUrl(path) {
  const token = localStorage.getItem('rdms_token') || ''
  return `${path}?token=${encodeURIComponent(token)}`
}

const PREVIEWABLE_EXT = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'pdf', 'txt', 'csv', 'log']

export function extOf(name) {
  const i = String(name || '').lastIndexOf('.')
  return i >= 0 ? String(name).slice(i + 1).toLowerCase() : ''
}

export function isPreviewable(name) {
  return PREVIEWABLE_EXT.includes(extOf(name))
}

export const KIND_LABEL = { raw: '原始数据', derived: '派生数据', backup: '备份文件' }
export const KIND_TAG = { raw: '', derived: 'warning', backup: 'info' }
export const OBJECT_KIND_LABEL = { cell: '细胞', animal: '动物', tissue: '组织', other: '其他' }

export const AUDIT_LABEL = {
  create: '创建',
  update: '修改',
  mark_used: '标记已用',
  unmark_used: '取消已用',
  delete: '移入回收站',
  restore: '恢复',
  hard_delete: '彻底删除',
}

export const FIELD_TYPE_LABEL = { text: '文本', number: '数字', date: '日期', select: '下拉' }
