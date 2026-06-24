import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { authAPI } from '@/api/auth'
import { adminAPI } from '@/api/admin'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem('user')) || null)
  const accessToken = ref(localStorage.getItem('access') || null)

  const isLoggedIn = computed(() => !!accessToken.value)
  const adminChecked = ref(JSON.parse(localStorage.getItem('is_admin') || 'false'))
  const isAdmin = computed(() => adminChecked.value)
  const fontSize = computed(() => user.value?.font_size || 'medium')

  const applyFontSize = (size) => {
    const root = document.documentElement
    if (size === 'small') root.style.setProperty('--base-font-size', '13px')
    else if (size === 'large') root.style.setProperty('--base-font-size', '20px')
    else if (size === 'xlarge') root.style.setProperty('--base-font-size', '24px')
    else root.style.setProperty('--base-font-size', '16px')
  }

  watch(fontSize, (newSize) => {
    applyFontSize(newSize)
  }, { immediate: true })

  const checkAdmin = async () => {
    try {
      await adminAPI.getUsers()
      adminChecked.value = true
      localStorage.setItem('is_admin', 'true')
    } catch {
      adminChecked.value = false
      localStorage.setItem('is_admin', 'false')
    }
  }

  const login = async (credentials) => {
    const { data } = await authAPI.login(credentials)
    user.value = data.user
    accessToken.value = data.access
    localStorage.setItem('access', data.access)
    localStorage.setItem('refresh', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
    await checkAdmin()
  }

  const logout = async () => {
    try {
      const refresh = localStorage.getItem('refresh')
      await authAPI.logout(refresh)
    } finally {
      user.value = null
      accessToken.value = null
      adminChecked.value = false
      localStorage.clear()
      document.documentElement.style.setProperty('--base-font-size', '16px')
    }
  }

  const fetchProfile = async () => {
    const { data } = await authAPI.getProfile()
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
  }

  return { user, accessToken, isLoggedIn, isAdmin, fontSize, login, logout, fetchProfile, checkAdmin }
})