import { defineStore } from 'pinia'
import api from '../api'

/** 项目 / 分类 / 对象 / 标签 / 自定义字段等全局配置数据 */
export const useConfigStore = defineStore('config', {
  state: () => ({
    projects: [],
    categories: [],
    objects: [],
    tags: [],
    fieldsByCategory: {}, // category_id -> 字段定义列表
    loaded: false,
  }),
  getters: {
    activeProjects: (s) => s.projects.filter((p) => p.status === 'active'),
    activeCategories: (s) => s.categories.filter((c) => c.is_active),
    projectById: (s) => (id) => s.projects.find((p) => p.id === id),
    categoryById: (s) => (id) => s.categories.find((c) => c.id === id),
    objectById: (s) => (id) => s.objects.find((o) => o.id === id),
  },
  actions: {
    async refreshAll() {
      const [projects, categories, objects, tags] = await Promise.all([
        api.get('/projects'), api.get('/categories'), api.get('/objects'), api.get('/tags'),
      ])
      this.projects = projects.data
      this.categories = categories.data
      this.objects = objects.data
      this.tags = tags.data
      this.loaded = true
    },
    async ensureLoaded() {
      if (!this.loaded) await this.refreshAll()
    },
    async loadFields(categoryId) {
      if (!categoryId) return []
      if (this.fieldsByCategory[categoryId]) return this.fieldsByCategory[categoryId]
      const { data } = await api.get('/custom-fields', { params: { category_id: categoryId } })
      this.fieldsByCategory[categoryId] = data
      return data
    },
    invalidateFields(categoryId) {
      delete this.fieldsByCategory[categoryId]
    },
    async findOrCreateTag(name) {
      const { data } = await api.post('/tags', { name })
      if (!this.tags.find((t) => t.id === data.id)) this.tags.push(data)
      return data
    },
    async findOrCreateObject(name, kind = 'other') {
      const exist = this.objects.find((o) => o.name === name)
      if (exist) return exist
      const { data } = await api.post('/objects', { name, kind })
      this.objects.push(data)
      return data
    },
  },
})
