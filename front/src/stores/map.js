import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMapStore = defineStore('map', () => {
  const pendingRoute = ref(null)

  const setRoute = (origin, dest) => {
    pendingRoute.value = { origin, dest }
  }

  const clearRoute = () => {
    pendingRoute.value = null
  }

  return { pendingRoute, setRoute, clearRoute }
})