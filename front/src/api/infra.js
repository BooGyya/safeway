import api from './index'

export const infraAPI = {
  getTrafficLights: (lat, lng, radius = 0.01) =>
    api.get('/api/infrastructure/traffic-lights/', { params: { lat, lng, radius } }),

  getAudioTrafficLights: (lat, lng) =>
    api.get('/api/infrastructure/traffic-lights/audio/', { params: { lat, lng } }),

  getRealtimeSignal: (itst_id) =>
    api.get('/api/infrastructure/traffic-lights/realtime/', { params: { itst_id } }),

  getFacilities: (lat, lng, type = null, radius = 0.01) =>
    api.get('/api/infrastructure/facilities/', { params: { lat, lng, radius, ...(type && { type }) } }),

  getElevators: (lat, lng) =>
    api.get('/api/infrastructure/elevators/', { params: { lat, lng } }),

  getSupportCenters: (lat, lng) =>
    api.get('/api/infrastructure/support-centers/', { params: { lat, lng } }),

  getCongestion: (area_nm) =>
    api.get('/api/infrastructure/congestion/', { params: { area_nm } }),

  getPlaces: (lat, lng, type) =>
    api.get('/api/infrastructure/places/', { params: { lat, lng, type } }),

  searchFacilities: (q, type = '') =>
    api.get('/api/infrastructure/facilities/search/', { params: { q, ...(type && { type }) } }),

  getFacilityDetail: (id) =>
    api.get(`/api/infrastructure/facilities/${id}/`),
}