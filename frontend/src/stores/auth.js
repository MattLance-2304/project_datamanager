import { defineStore } from 'pinia'
import api from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('rdms_token') || '',
    user: JSON.parse(localStorage.getItem('rdms_user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => s.user?.role === 'admin',
  },
  actions: {
    async login(username, password) {
      const { data } = await api.post('/auth/login', { username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('rdms_token', data.token)
      localStorage.setItem('rdms_user', JSON.stringify(data.user))
    },
    async fetchMe() {
      const { data } = await api.get('/auth/me')
      this.user = data
      localStorage.setItem('rdms_user', JSON.stringify(data))
    },
    async changePassword(oldPassword, newPassword) {
      await api.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('rdms_token')
      localStorage.removeItem('rdms_user')
    },
  },
})
