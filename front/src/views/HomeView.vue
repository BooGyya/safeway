<script setup>
import { ref, onMounted } from 'vue'
import { routeAPI } from '@/api/routes'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useMapStore } from '@/stores/map'

const auth = useAuthStore()
const router = useRouter()
const mapStore = useMapStore()

// 지도 관련
const mapContainer = ref(null)
let map = null
let markers = []
let polylines = []

// 경로 탐색 관련
const originQuery = ref('')
const destQuery = ref('')
const originResult = ref(null)
const destResult = ref(null)
const originSuggestions = ref([])
const destSuggestions = ref([])
const routeResult = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const transportType = ref('walk')

const transportOptions = [
  { value: 'walk', label: '🚶 도보' },
  { value: 'bus', label: '🚌 대중교통' },
  { value: 'taxi', label: '🚕 택시' },
]

onMounted(() => {
  const checkKakao = setInterval(() => {
    if (window.kakao && window.kakao.maps) {
      clearInterval(checkKakao)
      window.kakao.maps.load(() => {
        const options = {
          center: new window.kakao.maps.LatLng(37.5665, 126.9780),
          level: 5
        }
        map = new window.kakao.maps.Map(mapContainer.value, options)

        if (mapStore.pendingRoute) {
          const { origin, dest } = mapStore.pendingRoute
          originResult.value = origin
          originQuery.value = origin.name
          destResult.value = dest
          destQuery.value = dest.name
          mapStore.clearRoute()
          searchRoute()
        }
      })
    }
  }, 100)
})

const searchAddress = async (query, type) => {
  if (!query) {
    if (type === 'origin') originSuggestions.value = []
    else destSuggestions.value = []
    return
  }
  try {
    const { data } = await routeAPI.searchAddress(query)
    if (type === 'origin') originSuggestions.value = data
    else destSuggestions.value = data
  } catch (e) {
    console.error('주소 검색 실패', e.response?.status, e.response?.data)
  }
}

const selectOrigin = (place) => {
  originResult.value = place
  originQuery.value = place.name
  originSuggestions.value = []
}

const selectDest = (place) => {
  destResult.value = place
  destQuery.value = place.name
  destSuggestions.value = []
}

const clearMap = () => {
  markers.forEach(m => m.setMap(null))
  markers = []
  polylines.forEach(p => p.setMap(null))
  polylines = []
}

const searchRoute = async () => {
  if (!originResult.value || !destResult.value) {
    errorMsg.value = '출발지와 목적지를 선택해주세요.'
    return
  }
  errorMsg.value = ''
  loading.value = true
  try {
    const { data } = await routeAPI.search({
      origin_lat: originResult.value.lat,
      origin_lng: originResult.value.lng,
      origin_name: originResult.value.name,
      dest_lat: destResult.value.lat,
      dest_lng: destResult.value.lng,
      dest_name: destResult.value.name,
      transport_type: transportType.value,
    })
    routeResult.value = data
    drawRoute(data)
  } catch {
    errorMsg.value = '경로 탐색에 실패했습니다.'
  } finally {
    loading.value = false
  }
}

const drawRoute = (data) => {
  clearMap()
  const route = data.route
  const waypoints = route.waypoints

  const colorMap = {
    walk: '#2c7be5',
    bus: '#38a169',
    taxi: '#e53e3e'
  }
  const color = colorMap[transportType.value] || '#2c7be5'

  const path = waypoints.map(p => new window.kakao.maps.LatLng(p.lat, p.lng))
  const polyline = new window.kakao.maps.Polyline({
    path,
    strokeWeight: 5,
    strokeColor: color,
    strokeOpacity: 0.8,
  })
  polyline.setMap(map)
  polylines.push(polyline)

  const originMarker = new window.kakao.maps.Marker({
    position: new window.kakao.maps.LatLng(route.origin_lat, route.origin_lng),
    map,
  })
  const destMarker = new window.kakao.maps.Marker({
    position: new window.kakao.maps.LatLng(route.dest_lat, route.dest_lng),
    map,
  })
  markers.push(originMarker, destMarker)

  const bounds = new window.kakao.maps.LatLngBounds()
  path.forEach(p => bounds.extend(p))
  map.setBounds(bounds)

  if (data.nearby) {
    drawNearbyMarkers(data.nearby)
  }
}

const drawNearbyMarkers = (nearby) => {
  nearby.traffic_lights?.forEach(tl => {
    const marker = new window.kakao.maps.Marker({
      position: new window.kakao.maps.LatLng(tl.lat, tl.lng),
      map,
      title: tl.name,
    })
    markers.push(marker)
  })

  nearby.facilities?.forEach(f => {
    const marker = new window.kakao.maps.Marker({
      position: new window.kakao.maps.LatLng(f.lat, f.lng),
      map,
      title: f.name,
    })
    markers.push(marker)
  })
}

const addFavorite = async () => {
  if (!auth.isLoggedIn) {
    alert('로그인이 필요합니다.')
    router.push('/login')
    return
  }
  const nickname = prompt('즐겨찾기 이름을 입력하세요 (예: 집 → 회사)')
  if (!nickname) return
  try {
    await routeAPI.addFavorite({
      route_id: routeResult.value.route.id,
      nickname
    })
    alert('즐겨찾기에 추가되었습니다! ⭐')
  } catch {
    alert('즐겨찾기 추가에 실패했습니다.')
  }
}

const formatDuration = (seconds) => {
  const min = Math.floor(seconds / 60)
  return min < 60 ? `${min}분` : `${Math.floor(min/60)}시간 ${min%60}분`
}

const formatDistance = (meters) => {
  return meters >= 1000 ? `${(meters/1000).toFixed(1)}km` : `${Math.round(meters)}m`
}
</script>

<template>
  <div class="home">
    <div class="side-panel">
      <h2>경로 탐색</h2>

      <div class="transport-bar">
        <button
          v-for="opt in transportOptions"
          :key="opt.value"
          :class="['transport-btn', { active: transportType === opt.value }]"
          @click="transportType = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>

      <div class="search-box">
        <input
          v-model="originQuery"
          type="text"
          placeholder="출발지 검색"
          @keyup="searchAddress(originQuery, 'origin')"
        />
        <ul v-if="originSuggestions.length" class="suggestions">
          <li v-for="place in originSuggestions" :key="place.name" @click="selectOrigin(place)">
            <span class="place-name">{{ place.name }}</span>
            <span class="place-address">{{ place.address }}</span>
          </li>
        </ul>
      </div>

      <div class="search-box">
        <input
          v-model="destQuery"
          type="text"
          placeholder="목적지 검색"
          @keyup="searchAddress(destQuery, 'dest')"
        />
        <ul v-if="destSuggestions.length" class="suggestions">
          <li v-for="place in destSuggestions" :key="place.name" @click="selectDest(place)">
            <span class="place-name">{{ place.name }}</span>
            <span class="place-address">{{ place.address }}</span>
          </li>
        </ul>
      </div>

      <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

      <button @click="searchRoute" :disabled="loading" class="search-btn">
        {{ loading ? '탐색 중...' : '경로 탐색' }}
      </button>

      <div v-if="routeResult" class="route-result">
        <h3>경로 정보</h3>
        <div class="route-info">
          <div class="info-item">
            <span class="label">이동 수단</span>
            <span class="value">{{ transportOptions.find(t => t.value === transportType)?.label }}</span>
          </div>
          <div class="info-item">
            <span class="label">거리</span>
            <span class="value">{{ formatDistance(routeResult.route.distance) }}</span>
          </div>
          <div class="info-item">
            <span class="label">예상 시간</span>
            <span class="value">{{ formatDuration(routeResult.route.duration) }}</span>
          </div>
          <div class="info-item">
            <span class="label">안전 점수</span>
            <span class="value safety">{{ (routeResult.route.safety_score * 100).toFixed(0) }}점</span>
          </div>
        </div>

        <div v-if="routeResult.weather" class="weather-info">
          <p>🌤 {{ routeResult.weather.description }} {{ routeResult.weather.temp }}°C</p>
          <p v-if="routeResult.weather_applied" class="weather-warning">
            ⚠️ 악천후로 인해 이동시간이 20% 증가되었습니다.
          </p>
        </div>

        <div v-if="routeResult.nearby" class="nearby-info">
          <p>🚦 신호등 {{ routeResult.nearby.traffic_lights?.length || 0 }}개</p>
          <p>♿ 편의시설 {{ routeResult.nearby.facilities?.length || 0 }}개</p>
          <p>🏥 지원센터 {{ routeResult.nearby.support_centers?.length || 0 }}개</p>
        </div>

        <button v-if="auth.isLoggedIn" class="favorite-btn" @click="addFavorite">
          ⭐ 즐겨찾기 추가
        </button>
      </div>
    </div>

    <div ref="mapContainer" class="map"></div>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  height: calc(100vh - 60px);
}
.side-panel {
  width: 340px;
  background: white;
  padding: 20px;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
h2 {
  font-size: calc(var(--base-font-size, 16px) + 2px);
  color: #2c7be5;
  font-weight: bold;
}
.transport-bar {
  display: flex;
  gap: 8px;
}
.transport-btn {
  flex: 1;
  padding: 8px 4px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
  text-align: center;
}
.transport-btn.active {
  background: #2c7be5;
  color: white;
  border-color: #2c7be5;
}
.search-box {
  position: relative;
}
.search-box input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  outline: none;
  box-sizing: border-box;
}
.search-box input:focus {
  border-color: #2c7be5;
}
.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  list-style: none;
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.suggestions li {
  padding: 10px 14px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.suggestions li:hover {
  background-color: #f0f4ff;
}
.place-name {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: bold;
}
.place-address {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #888;
}
.search-btn {
  padding: 12px;
  background-color: #2c7be5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: var(--base-font-size, 16px);
  cursor: pointer;
}
.search-btn:disabled {
  background-color: #aaa;
}
.error {
  color: red;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.route-result {
  background: #f0f4ff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.route-result h3 {
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
  color: #333;
}
.route-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.info-item {
  display: flex;
  justify-content: space-between;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.label {
  color: #666;
}
.value {
  font-weight: bold;
}
.safety {
  color: #2c7be5;
}
.weather-info {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
  background: white;
  padding: 10px;
  border-radius: 8px;
}
.weather-warning {
  color: orange;
  margin-top: 4px;
}
.nearby-info {
  background: white;
  padding: 10px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
}
.favorite-btn {
  padding: 10px;
  background: white;
  border: 1px solid #2c7be5;
  color: #2c7be5;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: bold;
}
.map {
  flex: 1;
}
@media (max-width: 768px) {
  .home {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
    height: auto;
    max-height: 50vh;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  .map {
    height: 50vh;
  }
}
</style>