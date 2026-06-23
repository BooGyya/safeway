<script setup>
import { ref, onMounted, watch } from 'vue'
import { routeAPI } from '@/api/routes'
import { infraAPI } from '@/api/infra'
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
let categoryMarkers = {}

// 시설 카테고리
const categories = [
  { key: 'hospital', label: '병원', icon: '🏥', color: '#e53e3e' },
  { key: 'pharmacy', label: '약국', icon: '💊', color: '#38a169' },
  { key: 'welfare', label: '복지시설', icon: '🏢', color: '#805ad5' },
  { key: 'elevator', label: '엘리베이터', icon: '🛗', color: '#2c7be5' },
  { key: 'support_center', label: '지원센터', icon: '🤝', color: '#dd6b20' },
]
const activeCategories = ref(new Set())
let activeOverlay = null
let pinnedOverlay = null

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

        window.kakao.maps.event.addListener(map, 'click', () => {
          if (pinnedOverlay) {
            pinnedOverlay.setMap(null)
            pinnedOverlay = null
          }
          if (activeOverlay) {
            activeOverlay.setMap(null)
            activeOverlay = null
          }
        })

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

watch(transportType, () => {
  if (routeResult.value) {
    searchRoute()
  }
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
  Object.keys(categoryMarkers).forEach(key => clearCategoryMarkers(key))
  activeCategories.value = new Set()
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

  const path = waypoints.map(p => new window.kakao.maps.LatLng(p.lat, p.lng))
  const polyline = new window.kakao.maps.Polyline({
    path,
    strokeWeight: 5,
    strokeColor: '#2c7be5',
    strokeOpacity: 0.8,
  })
  polyline.setMap(map)
  polylines.push(polyline)

  const originPos = new window.kakao.maps.LatLng(route.origin_lat, route.origin_lng)
  const destPos = new window.kakao.maps.LatLng(route.dest_lat, route.dest_lng)

  const originMarker = new window.kakao.maps.Marker({ position: originPos, map })
  const destMarker = new window.kakao.maps.Marker({ position: destPos, map })
  markers.push(originMarker, destMarker)

  const originLabel = new window.kakao.maps.CustomOverlay({
    content: '<div class="route-marker-label route-marker-origin">출발</div>',
    position: originPos,
    yAnchor: 2.4,
    clickable: false,
  })
  const destLabel = new window.kakao.maps.CustomOverlay({
    content: '<div class="route-marker-label route-marker-dest">도착</div>',
    position: destPos,
    yAnchor: 2.4,
    clickable: false,
  })
  originLabel.setMap(map)
  destLabel.setMap(map)
  polylines.push(originLabel, destLabel)

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

const createCategoryMarkerImage = (color) => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="40" viewBox="0 0 28 40">
    <path d="M14 0C6.27 0 0 6.27 0 14c0 10.5 14 26 14 26s14-15.5 14-26C28 6.27 21.73 0 14 0z" fill="${color}"/>
    <circle cx="14" cy="14" r="7" fill="white"/>
  </svg>`
  const encoded = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
  return new window.kakao.maps.MarkerImage(
    encoded,
    new window.kakao.maps.Size(28, 40),
    { offset: new window.kakao.maps.Point(14, 40) }
  )
}

const createPlaceOverlay = (place, category, position) => {
  const content = document.createElement('div')
  content.className = 'marker-overlay'
  content.innerHTML = `
    <div class="marker-overlay-inner" style="border-top: 3px solid ${category.color}">
      <span class="marker-overlay-badge" style="background:${category.color}">
        ${category.icon} ${category.label}
      </span>
      <strong class="marker-overlay-name">${place.name}</strong>
      ${place.address ? `<p class="marker-overlay-row">📍 ${place.address}</p>` : ''}
      ${place.phone ? `<p class="marker-overlay-row">📞 <a href="tel:${place.phone}" class="marker-overlay-phone">${place.phone}</a></p>` : ''}
      ${place.distance ? `<p class="marker-overlay-row">📏 ${place.distance}m</p>` : ''}
      ${place.place_url ? `<p class="marker-overlay-row"><a href="${place.place_url}" target="_blank" rel="noopener" class="marker-overlay-link">상세 정보 보기 →</a></p>` : ''}
    </div>
    <div class="marker-overlay-arrow" style="border-top-color:white"></div>
  `

  content.addEventListener('click', (e) => {
    e.stopPropagation()
  })
  content.addEventListener('mouseenter', () => {
    overlay.setMap(map)
  })
  content.addEventListener('mouseleave', () => {
    if (pinnedOverlay !== overlay) {
      overlay.setMap(null)
      if (activeOverlay === overlay) activeOverlay = null
    }
  })

  const overlay = new window.kakao.maps.CustomOverlay({
    content,
    position,
    yAnchor: 1.15,
    zIndex: 30,
    clickable: true,
  })

  return overlay
}

const toggleCategory = async (categoryKey) => {
  if (activeCategories.value.has(categoryKey)) {
    activeCategories.value.delete(categoryKey)
    activeCategories.value = new Set(activeCategories.value)
    clearCategoryMarkers(categoryKey)
    return
  }

  activeCategories.value.add(categoryKey)
  activeCategories.value = new Set(activeCategories.value)

  const center = map.getCenter()
  const lat = center.getLat()
  const lng = center.getLng()
  const category = categories.find(c => c.key === categoryKey)

  try {
    let places = []

    if (categoryKey === 'elevator') {
      const { data } = await infraAPI.getElevators(lat, lng)
      places = Array.isArray(data) ? data : data.results || []
    } else if (categoryKey === 'support_center') {
      const { data } = await infraAPI.getSupportCenters(lat, lng)
      places = Array.isArray(data) ? data : data.results || []
    } else {
      const { data } = await infraAPI.getPlaces(lat, lng, categoryKey)
      places = data.results || []
    }

    const markerImage = createCategoryMarkerImage(category.color)
    const newMarkers = []

    places.forEach(place => {
      if (!place.lat || !place.lng) return
      const position = new window.kakao.maps.LatLng(place.lat, place.lng)
      const marker = new window.kakao.maps.Marker({
        position,
        map,
        title: place.name,
        image: markerImage,
      })

      const overlay = createPlaceOverlay(place, category, position)

      window.kakao.maps.event.addListener(marker, 'mouseover', () => {
        if (pinnedOverlay === overlay) return
        if (activeOverlay && activeOverlay !== pinnedOverlay) activeOverlay.setMap(null)
        overlay.setMap(map)
        activeOverlay = overlay
      })

      window.kakao.maps.event.addListener(marker, 'mouseout', () => {
        if (pinnedOverlay === overlay) return
        overlay.setMap(null)
        if (activeOverlay === overlay) activeOverlay = null
      })

      window.kakao.maps.event.addListener(marker, 'click', () => {
        if (pinnedOverlay === overlay) {
          pinnedOverlay = null
          overlay.setMap(null)
          activeOverlay = null
          return
        }
        if (pinnedOverlay) pinnedOverlay.setMap(null)
        if (activeOverlay && activeOverlay !== overlay) activeOverlay.setMap(null)
        overlay.setMap(map)
        pinnedOverlay = overlay
        activeOverlay = overlay
      })

      newMarkers.push(marker)
    })

    categoryMarkers[categoryKey] = newMarkers
  } catch (e) {
    console.error(`${categoryKey} 시설 조회 실패`, e)
    activeCategories.value.delete(categoryKey)
    activeCategories.value = new Set(activeCategories.value)
  }
}

const clearCategoryMarkers = (categoryKey) => {
  if (categoryMarkers[categoryKey]) {
    categoryMarkers[categoryKey].forEach(m => m.setMap(null))
    delete categoryMarkers[categoryKey]
  }
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

// 현재 위치로 이동
const moveToCurrentLocation = () => {
  if (!navigator.geolocation) {
    alert('위치 정보를 지원하지 않는 브라우저입니다.')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude
      const lng = pos.coords.longitude
      const position = new window.kakao.maps.LatLng(lat, lng)
      map.setCenter(position)
      map.setLevel(3)
    },
    () => alert('위치 정보를 가져오지 못했습니다.'),
    {
      enableHighAccuracy: true,  // GPS 우선 사용
      timeout: 10000,
      maximumAge: 0
    }
  )
}

// 확대
const zoomIn = () => {
  map.setLevel(map.getLevel() - 1)
}

// 축소
const zoomOut = () => {
  map.setLevel(map.getLevel() + 1)
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

    <!-- 지도 -->
    <div class="map-wrapper">
      <!-- 시설 카테고리 필터 -->
      <div class="category-bar">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['category-chip', { active: activeCategories.has(cat.key) }]"
          :style="activeCategories.has(cat.key) ? { background: cat.color, borderColor: cat.color } : {}"
          @click="toggleCategory(cat.key)"
        >
          <span class="chip-icon">{{ cat.icon }}</span>
          <span class="chip-label">{{ cat.label }}</span>
        </button>
      </div>

      <div ref="mapContainer" class="map"></div>

      <!-- 지도 컨트롤 버튼 -->
      <div class="map-controls">
        <button @click="moveToCurrentLocation" class="control-btn location-btn" title="현재 위치">
          📍
        </button>
        <button @click="zoomIn" class="control-btn" title="확대">
          +
        </button>
        <button @click="zoomOut" class="control-btn" title="축소">
          −
        </button>
      </div>
    </div>
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
.label { color: #666; }
.value { font-weight: bold; }
.safety { color: #2c7be5; }
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

/* 시설 카테고리 */
.category-bar {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 10;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.category-bar::-webkit-scrollbar {
  display: none;
}
.category-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  background: white;
  border: 1.5px solid #ddd;
  border-radius: 20px;
  cursor: pointer;
  white-space: nowrap;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #444;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  transition: all 0.2s;
}
.category-chip:hover {
  border-color: #aaa;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.category-chip.active {
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.chip-icon {
  font-size: calc(var(--base-font-size, 16px) - 1px);
}
.chip-label {
  font-weight: 600;
}

/* 지도 */
.map-wrapper {
  flex: 1;
  position: relative;
}
.map {
  width: 100%;
  height: 100%;
}
.map-controls {
  position: absolute;
  bottom: 32px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
}
.control-btn {
  width: 40px;
  height: 40px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
  transition: background 0.2s;
}
.control-btn:hover {
  background: #f0f4ff;
}
.location-btn {
  font-size: 20px;
}

@media (max-width: 768px) {
  .home { flex-direction: column; }
  .side-panel {
    width: 100%;
    height: auto;
    max-height: 50vh;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  .map-wrapper { height: 50vh; }
}
</style>

<!-- 마커 오버레이: 카카오 지도가 Vue 외부에 렌더링하므로 global style 필요 -->
<style>
.marker-overlay {
  position: relative;
  cursor: default;
}
.marker-overlay-inner {
  background: white;
  border-radius: 12px;
  padding: 12px 14px;
  min-width: 180px;
  max-width: 260px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
  display: flex;
  flex-direction: column;
  gap: 5px;
  line-height: 1.4;
  font-family: 'Pretendard', -apple-system, sans-serif;
}
.marker-overlay-badge {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 3px;
  padding: 2px 8px;
  border-radius: 10px;
  color: white;
  font-size: 11px;
  font-weight: 600;
}
.marker-overlay-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #222;
  word-break: keep-all;
}
.marker-overlay-row {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.marker-overlay-phone {
  color: #2c7be5;
  text-decoration: none;
}
.marker-overlay-phone:hover {
  text-decoration: underline;
}
.marker-overlay-link {
  color: #2c7be5;
  text-decoration: none;
  font-weight: 600;
}
.marker-overlay-link:hover {
  text-decoration: underline;
}
.marker-overlay-arrow {
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 10px solid white;
  margin: 0 auto;
  filter: drop-shadow(0 2px 2px rgba(0,0,0,0.1));
}

/* 출발/도착 마커 라벨 */
.route-marker-label {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  color: white;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  font-family: 'Pretendard', -apple-system, sans-serif;
}
.route-marker-origin {
  background: #2c7be5;
}
.route-marker-dest {
  background: #e53e3e;
}

@media (max-width: 768px) {
  .marker-overlay-inner {
    min-width: 160px;
    max-width: 220px;
    padding: 10px 12px;
    gap: 4px;
  }
  .marker-overlay-badge {
    font-size: 10px;
    padding: 2px 6px;
  }
  .marker-overlay-name {
    font-size: 13px;
  }
  .marker-overlay-row {
    font-size: 11px;
  }
  .route-marker-label {
    font-size: 11px;
    padding: 2px 8px;
  }
}
</style>