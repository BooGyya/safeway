<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { routeAPI } from '@/api/routes'
import { infraAPI } from '@/api/infra'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useMapStore } from '@/stores/map'
import { authAPI } from '@/api/auth'
import { communityAPI } from '@/api/community'
let originDebounceTimer = null
let destDebounceTimer = null

const onOriginInput = () => {
  clearTimeout(originDebounceTimer)
  originDebounceTimer = setTimeout(() => {
    searchAddress(originQuery.value, 'origin')
  }, 300)
}

const onDestInput = () => {
  clearTimeout(destDebounceTimer)
  destDebounceTimer = setTimeout(() => {
    searchAddress(destQuery.value, 'dest')
  }, 300)
}

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
  { key: 'hospital', label: '병원', icon: '🏥', color: '#4AADE8' },
  { key: 'pharmacy', label: '약국', icon: '💊', color: '#F5C542' },
  { key: 'welfare', label: '복지시설', icon: '🏢', color: '#805ad5' },
  { key: 'elevator', label: '엘리베이터', icon: '🛗', color: '#8B5E3C' },
]
const activeCategories = ref(new Set())
let activeOverlay = null
let pinnedOverlay = null
let dangerZoneMarkers = []

// 서울 실시간 도시데이터에서 조회 가능한 것으로 확인된 주요 지역 (AREA_NM)
const CONGESTION_AREAS = [
  { name: '강남역', lat: 37.4979, lng: 127.0276 },
  { name: '홍대 관광특구', lat: 37.5572, lng: 126.9254 },
  { name: '명동 관광특구', lat: 37.5636, lng: 126.9850 },
  { name: '동대문 관광특구', lat: 37.5714, lng: 127.0098 },
  { name: '이태원 관광특구', lat: 37.5345, lng: 126.9947 },
  { name: '종로·청계 관광특구', lat: 37.5704, lng: 126.9919 },
  { name: '잠실 관광특구', lat: 37.5133, lng: 127.1001 },
  { name: '신촌·이대역', lat: 37.5599, lng: 126.9425 },
  { name: '여의도', lat: 37.5219, lng: 126.9245 },
  { name: '광화문·덕수궁', lat: 37.5717, lng: 126.9764 },
  { name: '잠실종합운동장', lat: 37.5145, lng: 127.0726 },
  { name: '서울역', lat: 37.5547, lng: 126.9707 },
  { name: '강남 MICE 관광특구', lat: 37.5115, lng: 127.0595 },
  { name: '건대입구역', lat: 37.5403, lng: 127.0700 },
  { name: '신림역', lat: 37.4842, lng: 126.9296 },
  { name: '노량진', lat: 37.5135, lng: 126.9425 },
  { name: '가산디지털단지역', lat: 37.4818, lng: 126.8825 },
  { name: '용산역', lat: 37.5299, lng: 126.9648 },
  { name: '왕십리역', lat: 37.5615, lng: 127.0370 },
  { name: '연남동', lat: 37.5635, lng: 126.9255 },
  { name: '압구정로데오거리', lat: 37.5274, lng: 127.0402 },
  { name: '성수카페거리', lat: 37.5446, lng: 127.0559 },
  { name: '발산역', lat: 37.5586, lng: 126.8378 },
  { name: '보라매공원', lat: 37.4926, lng: 126.9213 },
  { name: '뚝섬한강공원', lat: 37.5298, lng: 127.0640 },
]
const congestionActive = ref(false)
const congestionInfo = ref(null)
const congestionLoading = ref(false)

const findNearestCongestionArea = (lat, lng) => {
  let nearest = null
  let minDist = Infinity
  for (const area of CONGESTION_AREAS) {
    const d = Math.hypot(area.lat - lat, area.lng - lng)
    if (d < minDist) {
      minDist = d
      nearest = area
    }
  }
  return nearest
}

const toggleCongestion = async (areaOverride = null) => {
  if (congestionActive.value && !areaOverride) {
    congestionActive.value = false
    congestionInfo.value = null
    return
  }
  congestionActive.value = true
  congestionLoading.value = true
  try {
    const center = map.getCenter()
    const area = areaOverride || findNearestCongestionArea(center.getLat(), center.getLng())
    const { data } = await infraAPI.getCongestion(area.name)
    congestionInfo.value = {
      area: area.name,
      level: data.congestion_lvl,
      message: data.congestion_msg,
    }
  } catch (e) {
    console.error('혼잡도 조회 실패', e)
    congestionInfo.value = { area: '', level: '', message: '혼잡도 정보를 가져오지 못했습니다.' }
  } finally {
    congestionLoading.value = false
  }
}

// 카카오맵 내장 실시간 도로 교통정보 레이어
const trafficActive = ref(false)
const toggleTraffic = () => {
  if (trafficActive.value) {
    map.removeOverlayMapTypeId(window.kakao.maps.MapTypeId.TRAFFIC)
  } else {
    map.addOverlayMapTypeId(window.kakao.maps.MapTypeId.TRAFFIC)
  }
  trafficActive.value = !trafficActive.value
}

const congestionLevelColor = (level) => ({
  '여유': '#2eb872',
  '보통': '#2eb872',
  '약간 붐빔': '#f5a623',
  '붐빔': '#e53e3e',
  '매우 붐빔': '#e53e3e',
}[level] || '#666')

// 패널 모드
const panelMode = ref('route')

// 시설 검색 관련
const facilityQuery = ref('')
const facilityResults = ref([])
const facilityLoading = ref(false)
const selectedFacility = ref(null)
const facilitySearchHistory = ref(JSON.parse(localStorage.getItem('facilitySearchHistory') || '[]'))
let facilityMarkers = []

// 지도 클릭 위치 정보
const clickedPlace = ref(null)
const previewMapContainer = ref(null)
let clickedMarker = null
let previewMap = null

// 경로 탐색 관련
const originQuery = ref('')
const destQuery = ref('')
const originResult = ref(null)
const destResult = ref(null)
const originSuggestions = ref([])
const destSuggestions = ref([])
const routeResult = ref(null)
const nearbyOriginFacilities = ref([])
const nearbyDestFacilities = ref([])
const loading = ref(false)
const errorMsg = ref('')
const transportType = ref('walk')

const transportOptions = [
  { value: 'walk', label: '🚶 도보' },
  { value: 'bus', label: '🚌 대중교통' },
  { value: 'taxi', label: '🚕 택시' },
]

const selectedUserType = ref('normal')
const walkSpeed = ref(1.0)
const showRouteDetail = ref(false)
const detailGroupOpen = ref({ hospitals: false, pharmacies: false, welfare: false })
const toggleDetailGroup = (key) => {
  detailGroupOpen.value[key] = !detailGroupOpen.value[key]
}
const activeRouteTab = ref('recommend')
const routeTabs = [
  { key: 'recommend', label: '추천' },
  { key: 'stair_free', label: '계단회피' },
  { key: 'main_road', label: '큰길우선' },
  { key: 'weather', label: '날씨추천' },
]
const routeDescriptions = {
  recommend: 'TMAP 추천 알고리즘 경로',
  stair_free: '계단 없는 경로',
  main_road: '대로 위주의 넓은 도로 경로',
  weather: '비 올 때 예상 소요시간',
}
const fastestRouteKey = computed(() => {
  if (!routeResult.value?.routes) return null
  let best = null
  let bestDuration = Infinity
  for (const key of ['recommend', 'stair_free', 'main_road']) {
    const duration = routeResult.value.routes[key]?.duration
    if (duration != null && duration < bestDuration) {
      bestDuration = duration
      best = key
    }
  }
  return best
})
const transitModeIcon = (mode) => ({ WALK: '🚶', BUS: '🚌', SUBWAY: '🚇' }[mode] || '🚏')
const currentNearby = computed(() => {
  if (!routeResult.value) return null
  if (routeResult.value.routes) {
    return routeResult.value.routes[activeRouteTab.value]?.nearby || null
  }
  return routeResult.value.nearby || null
})

const selectedDetailFacility = ref(null)
let focusedMarker = null

// 실시간 보행신호 잔여시간을 1초마다 줄어들게 표시하기 위한 시계
const nowTick = ref(Date.now())
let signalTickInterval = null
const remainingSignalSeconds = (tl) => {
  if (tl.realtime_pedestrian_sec == null || !tl.realtime_fetched_at) return null
  const elapsed = (nowTick.value - new Date(tl.realtime_fetched_at).getTime()) / 1000
  return Math.max(0, Math.round(tl.realtime_pedestrian_sec - elapsed))
}

// 신호가 0초가 됐을 때 동시에 여러 번 재조회하지 않도록 막는 가드
const refreshingSignalIds = new Set()

const refreshOneSignal = async (tl) => {
  if (refreshingSignalIds.has(tl.id)) return
  refreshingSignalIds.add(tl.id)
  try {
    const { data } = await routeAPI.getRealtimeSignal(tl.lat, tl.lng)
    tl.realtime_pedestrian_sec = data.realtime_pedestrian_sec
    tl.realtime_fetched_at = data.realtime_fetched_at
  } catch { /* ignore */ } finally {
    refreshingSignalIds.delete(tl.id)
  }
}

// 상세보기를 여는 시점 기준으로 실시간 보행신호를 다시 조회 (검색 시점 스냅샷이 그새 0이 되는 것 방지)
const refreshRealtimeSignals = async () => {
  const lights = currentNearby.value?.traffic_lights || []
  await Promise.all(
    lights.filter((tl) => tl.realtime_pedestrian_sec != null).map(refreshOneSignal)
  )
}

// 카운트다운이 0초에 도달하면(신호가 바뀌었을 시점) 자동으로 한 번 더 조회해서 다시 줄어들게 함
const refreshZeroedSignals = () => {
  if (!showRouteDetail.value) return
  const lights = currentNearby.value?.traffic_lights || []
  lights
    .filter((tl) => tl.realtime_pedestrian_sec != null && remainingSignalSeconds(tl) === 0)
    .forEach(refreshOneSignal)
}

watch(showRouteDetail, (open) => {
  if (open) refreshRealtimeSignals()
})

onMounted(() => {
  signalTickInterval = setInterval(() => {
    nowTick.value = Date.now()
    refreshZeroedSignals()
  }, 1000)

  const checkKakao = setInterval(() => {
    if (window.kakao && window.kakao.maps) {
      clearInterval(checkKakao)
      window.kakao.maps.load(() => {
        const options = {
          center: new window.kakao.maps.LatLng(37.5665, 126.9780),
          level: 5
        }
        map = new window.kakao.maps.Map(mapContainer.value, options)

        if (auth.user) {
          selectedUserType.value = auth.user.user_type || 'normal'
          walkSpeed.value = auth.user.walk_speed || 1.0
        }

        window.kakao.maps.event.addListener(map, 'click', (mouseEvent) => {
          if (pinnedOverlay) {
            pinnedOverlay.setMap(null)
            pinnedOverlay = null
          }
          if (activeOverlay) {
            activeOverlay.setMap(null)
            activeOverlay = null
          }
          handleMapClick(mouseEvent.latLng)
        })

        loadDangerZones()

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

onUnmounted(() => {
  if (signalTickInterval) clearInterval(signalTickInterval)
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
    // 응답이 늦게 와서 그 사이 입력값이 바뀌었으면 오래된 결과는 버린다
    const currentQuery = type === 'origin' ? originQuery.value : destQuery.value
    if (currentQuery !== query) return
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
      user_type: selectedUserType.value,
      walk_speed: walkSpeed.value,
    })
    routeResult.value = data
    if (data.routes) {
      activeRouteTab.value = 'recommend'
      drawWalkRoute(data, 'recommend')
    } else {
      drawRoute(data)
    }
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
    strokeWeight: 7,
    strokeColor: '#3366FF',
    strokeOpacity: 0.9,
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

const drawWalkRoute = (data, tabKey) => {
  clearMap()
  const routeData = data.routes[tabKey]
  if (!routeData) return

  const waypoints = routeData.waypoints
  const path = waypoints.map(p => new window.kakao.maps.LatLng(p.lat, p.lng))
  const polyline = new window.kakao.maps.Polyline({
    path,
    strokeWeight: 7,
    strokeColor: '#3366FF',
    strokeOpacity: 0.9,
  })
  polyline.setMap(map)
  polylines.push(polyline)

  const first = waypoints[0]
  const last = waypoints[waypoints.length - 1]
  const originPos = new window.kakao.maps.LatLng(first.lat, first.lng)
  const destPos = new window.kakao.maps.LatLng(last.lat, last.lng)

  const originMarker = new window.kakao.maps.Marker({ position: originPos, map })
  const destMarker = new window.kakao.maps.Marker({ position: destPos, map })
  markers.push(originMarker, destMarker)

  const originLabel = new window.kakao.maps.CustomOverlay({
    content: '<div class="route-marker-label route-marker-origin">출발</div>',
    position: originPos, yAnchor: 2.4, clickable: false,
  })
  const destLabel = new window.kakao.maps.CustomOverlay({
    content: '<div class="route-marker-label route-marker-dest">도착</div>',
    position: destPos, yAnchor: 2.4, clickable: false,
  })
  originLabel.setMap(map)
  destLabel.setMap(map)
  polylines.push(originLabel, destLabel)

  const bounds = new window.kakao.maps.LatLngBounds()
  path.forEach(p => bounds.extend(p))
  map.setBounds(bounds)

  if (routeData.nearby) drawNearbyMarkers(routeData.nearby)
}

const switchRouteTab = (tabKey) => {
  activeRouteTab.value = tabKey
  if (routeResult.value?.routes) {
    drawWalkRoute(routeResult.value, tabKey)
  }
}

const fetchNearbyFacilities = async (route) => {
  nearbyOriginFacilities.value = []
  nearbyDestFacilities.value = []
  try {
    const [originRes, destRes] = await Promise.allSettled([
      infraAPI.getPlaces(route.origin_lat, route.origin_lng, 'hospital'),
      infraAPI.getPlaces(route.dest_lat, route.dest_lng, 'hospital'),
    ])
    const [originPharm, destPharm] = await Promise.allSettled([
      infraAPI.getPlaces(route.origin_lat, route.origin_lng, 'pharmacy'),
      infraAPI.getPlaces(route.dest_lat, route.dest_lng, 'pharmacy'),
    ])
    const oHosp = originRes.status === 'fulfilled' ? (originRes.value.data.results || []).slice(0, 3) : []
    const oPharm = originPharm.status === 'fulfilled' ? (originPharm.value.data.results || []).slice(0, 3) : []
    const dHosp = destRes.status === 'fulfilled' ? (destRes.value.data.results || []).slice(0, 3) : []
    const dPharm = destPharm.status === 'fulfilled' ? (destPharm.value.data.results || []).slice(0, 3) : []
    nearbyOriginFacilities.value = [...oHosp.map(p => ({...p, type: '병원'})), ...oPharm.map(p => ({...p, type: '약국'}))]
    nearbyDestFacilities.value = [...dHosp.map(p => ({...p, type: '병원'})), ...dPharm.map(p => ({...p, type: '약국'}))]
  } catch { /* 무시 */ }
}

const createEmojiMarkerImage = (emoji, size = 28) => {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  ctx.font = `${size - 4}px serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(emoji, size / 2, size / 2)
  return new window.kakao.maps.MarkerImage(
    canvas.toDataURL(),
    new window.kakao.maps.Size(size, size),
    { offset: new window.kakao.maps.Point(size / 2, size / 2) }
  )
}

const addOverlayMarkers = (items, color, icon, label, useEmoji = false) => {
  const markerImage = useEmoji ? createEmojiMarkerImage(icon, 30) : createCategoryMarkerImage(color)
  items?.forEach(item => {
    if (!item.lat || !item.lng) return
    const position = new window.kakao.maps.LatLng(item.lat, item.lng)
    const marker = new window.kakao.maps.Marker({
      position, map,
      title: item.name || item.title || '',
      image: markerImage,
      zIndex: color === '#e53e3e' ? 50 : 10,
    })
    const overlay = createPlaceOverlay(
      { name: item.name || item.title, address: item.address || '', phone: item.phone || '', place_url: item.place_url || '', category: item.category_label || '' },
      { color, icon, label },
      position
    )
    window.kakao.maps.event.addListener(marker, 'mouseover', () => {
      if (activeOverlay && activeOverlay !== pinnedOverlay) activeOverlay.setMap(null)
      overlay.setMap(map); activeOverlay = overlay
    })
    window.kakao.maps.event.addListener(marker, 'mouseout', () => {
      if (pinnedOverlay !== overlay) { overlay.setMap(null); if (activeOverlay === overlay) activeOverlay = null }
    })
    window.kakao.maps.event.addListener(marker, 'click', () => {
      if (pinnedOverlay === overlay) { pinnedOverlay = null; overlay.setMap(null); activeOverlay = null; return }
      if (pinnedOverlay) pinnedOverlay.setMap(null)
      overlay.setMap(map); pinnedOverlay = overlay; activeOverlay = overlay
    })
    markers.push(marker)
  })
}

const drawNearbyMarkers = (nearby) => {
  addOverlayMarkers(nearby.traffic_lights?.map(tl => ({ ...tl, name: tl.description || tl.road_nm || '신호등' })), '#2eb872', '🚦', '신호등', true)
  addOverlayMarkers(nearby.hospitals, '#4AADE8', '🏥', '병원')
  addOverlayMarkers(nearby.pharmacies, '#F5C542', '💊', '약국')
  addOverlayMarkers(nearby.welfare, '#805ad5', '🏢', '복지시설')

  const dangerIcons = { danger: '⚠️', obstacle: '🚧', broken: '🔨', construction: '🏗️' }
  nearby.danger_zones?.forEach(dz => {
    addOverlayMarkers([{ ...dz, name: dz.title }], '#e53e3e', dangerIcons[dz.category] || '⚠️', dz.category_label || '위험')
  })
}

const dangerCategoryIcons = { danger: '⚠️', obstacle: '🚧', broken: '🔨', construction: '🏗️' }

const loadDangerZones = async () => {
  dangerZoneMarkers.forEach(m => m.setMap(null))
  dangerZoneMarkers = []
  try {
    const { data } = await communityAPI.getDangerZones()
    data.forEach(dz => {
      if (!dz.lat || !dz.lng) return
      const position = new window.kakao.maps.LatLng(dz.lat, dz.lng)
      const markerImage = createCategoryMarkerImage('#e53e3e')
      const marker = new window.kakao.maps.Marker({
        position, map,
        title: dz.title,
        image: markerImage,
        zIndex: 50,
      })
      const overlay = createPlaceOverlay(
        { name: dz.title, address: dz.address, category: dz.category_label },
        { color: '#e53e3e', icon: dangerCategoryIcons[dz.category] || '⚠️', label: dz.category_label },
        position
      )
      window.kakao.maps.event.addListener(marker, 'mouseover', () => {
        if (activeOverlay && activeOverlay !== pinnedOverlay) activeOverlay.setMap(null)
        overlay.setMap(map); activeOverlay = overlay
      })
      window.kakao.maps.event.addListener(marker, 'mouseout', () => {
        if (pinnedOverlay !== overlay) { overlay.setMap(null); if (activeOverlay === overlay) activeOverlay = null }
      })
      window.kakao.maps.event.addListener(marker, 'click', () => {
        if (pinnedOverlay === overlay) { pinnedOverlay = null; overlay.setMap(null); activeOverlay = null; return }
        if (pinnedOverlay) pinnedOverlay.setMap(null)
        overlay.setMap(map); pinnedOverlay = overlay; activeOverlay = overlay
      })
      dangerZoneMarkers.push(marker)
    })
  } catch { /* 무시 */ }
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
    <div class="marker-overlay-inner" style="border-left: 4px solid ${category.color}">
      <button class="marker-overlay-close">✕</button>
      <div class="marker-overlay-head">
        <span class="marker-overlay-icon-big">${category.icon}</span>
        <div class="marker-overlay-head-text">
          <strong class="marker-overlay-name">${place.name}</strong>
          <span class="marker-overlay-label" style="color:${category.color}">${category.label}</span>
        </div>
      </div>
      ${place.address ? `<p class="marker-overlay-row">📍 ${place.address}</p>` : ''}
      ${place.phone ? `<p class="marker-overlay-row">📞 <a href="tel:${place.phone}" class="marker-overlay-phone">${place.phone}</a></p>` : ''}
      ${place.description ? `<p class="marker-overlay-row">📝 ${place.description}</p>` : ''}
      ${place.place_url ? `<a href="${place.place_url}" target="_blank" rel="noopener" class="marker-overlay-detail-btn">상세정보 보기 →</a>` : ''}
    </div>
    <div class="marker-overlay-arrow"></div>
  `

  content.addEventListener('click', (e) => {
    e.stopPropagation()
  })

  content.querySelector('.marker-overlay-close').addEventListener('click', () => {
    overlay.setMap(null)
    if (pinnedOverlay === overlay) pinnedOverlay = null
    if (activeOverlay === overlay) activeOverlay = null
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
    zIndex: 999,
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
      places = data.results || []
    } else if (categoryKey === 'support_center') {
      const { data } = await infraAPI.getSupportCenters(lat, lng)
      places = Array.isArray(data) ? data : data.results || []
    } else {
      const { data } = await infraAPI.getPlaces(lat, lng, categoryKey)
      places = data.results || []
    }

    // 이하 마커 생성 코드는 기존과 동일
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
    let routeId = routeResult.value.route?.id
    if (!routeId) {
      const { data: historyData } = await routeAPI.getHistory()
      if (historyData.length > 0) {
        routeId = historyData[0].route?.id
      }
    }
    if (!routeId) {
      alert('경로 정보를 찾을 수 없습니다.')
      return
    }
    await routeAPI.addFavorite({
      route_id: routeId,
      nickname
    })
    alert('즐겨찾기에 추가되었습니다!')
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

const sendSOS = async () => {
  if (!auth.isLoggedIn) {
    alert('로그인이 필요합니다.')
    return
  }
  if (!auth.user?.sos_number) {
    alert('마이페이지에서 SOS 번호를 먼저 등록해주세요!')
    router.push('/profile')
    return
  }
  if (!confirm('SOS 문자를 발송하시겠습니까?')) return

  try {
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        await authAPI.sendSOS({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
        })
        alert('SOS 문자가 발송되었습니다!')
      },
      async () => {
        await authAPI.sendSOS({})
        alert('SOS 문자가 발송되었습니다!')
      }
    )
  } catch {
    alert('SOS 발송에 실패했습니다.')
  }
}

const addSearchHistory = (keyword) => {
  const filtered = facilitySearchHistory.value.filter(h => h !== keyword)
  filtered.unshift(keyword)
  facilitySearchHistory.value = filtered.slice(0, 10)
  localStorage.setItem('facilitySearchHistory', JSON.stringify(facilitySearchHistory.value))
}

const removeSearchHistory = (keyword) => {
  facilitySearchHistory.value = facilitySearchHistory.value.filter(h => h !== keyword)
  localStorage.setItem('facilitySearchHistory', JSON.stringify(facilitySearchHistory.value))
}

const clearAllSearchHistory = () => {
  facilitySearchHistory.value = []
  localStorage.removeItem('facilitySearchHistory')
}

const searchFromHistory = (keyword) => {
  facilityQuery.value = keyword
  searchFacility()
}

// 시설 검색 (카카오 SDK 직접 사용으로 상세정보 확보)
const searchFacility = async () => {
  if (!facilityQuery.value.trim()) return
  addSearchHistory(facilityQuery.value.trim())
  facilityLoading.value = true
  facilityResults.value = []
  selectedFacility.value = null
  clearFacilityMarkers()

  const center = map.getCenter()
  const ps = new window.kakao.maps.services.Places()

  ps.keywordSearch(
    facilityQuery.value,
    (data, status) => {
      facilityLoading.value = false
      if (status !== window.kakao.maps.services.Status.OK || !data.length) {
        facilityResults.value = []
        return
      }
      facilityResults.value = data.map(doc => ({
        name: doc.place_name,
        address: doc.road_address_name || doc.address_name,
        jibun: doc.address_name || '',
        lat: parseFloat(doc.y),
        lng: parseFloat(doc.x),
        phone: doc.phone || '',
        category: doc.category_name || '',
        place_url: doc.place_url || '',
        distance: doc.distance || '',
      }))

      facilityResults.value.forEach(f => {
        if (!f.lat || !f.lng) return
        const marker = new window.kakao.maps.Marker({
          position: new window.kakao.maps.LatLng(f.lat, f.lng),
          map,
        })
        window.kakao.maps.event.addListener(marker, 'click', () => selectFacility(f))
        facilityMarkers.push(marker)
      })

      const bounds = new window.kakao.maps.LatLngBounds()
      facilityResults.value.forEach(f => {
        if (f.lat && f.lng) bounds.extend(new window.kakao.maps.LatLng(f.lat, f.lng))
      })
      map.setBounds(bounds)
    },
    { location: center, size: 15, sort: 'distance' }
  )
}

const selectFacility = (facility) => {
  selectedFacility.value = facility
  if (facility.lat && facility.lng) {
    map.setCenter(new window.kakao.maps.LatLng(facility.lat, facility.lng))
    map.setLevel(3)
  }
}

const clearFacilityMarkers = () => {
  facilityMarkers.forEach(m => m.setMap(null))
  facilityMarkers = []
}

let focusedOverlay = null

const focusFacilityOnMap = (facility) => {
  if (focusedMarker) {
    focusedMarker.setMap(null)
    focusedMarker = null
  }
  if (focusedOverlay) {
    focusedOverlay.setMap(null)
    focusedOverlay = null
  }

  if (selectedDetailFacility.value?.id === facility.id) {
    selectedDetailFacility.value = null
    return
  }

  selectedDetailFacility.value = facility
  if (!facility.lat || !facility.lng) return

  const position = new window.kakao.maps.LatLng(facility.lat, facility.lng)
  const markerImage = createCategoryMarkerImage('#FF6B00')

  focusedMarker = new window.kakao.maps.Marker({ position, map, image: markerImage, zIndex: 100 })

  const typeLabel = facilityTypeLabel(facility.facility_type)
  const category = {
    color: '#FF6B00',
    icon: '♿',
    label: typeLabel || '편의시설',
  }
  const placeData = {
    name: facility.name,
    address: facility.address || '',
    phone: '',
    distance: '',
    place_url: '',
  }
  focusedOverlay = createPlaceOverlay(placeData, category, position)
  focusedOverlay.setMap(map)
  pinnedOverlay = focusedOverlay

  map.setCenter(position)
  map.setLevel(3)
}

const facilityTypeLabel = (type) => {
  const map = { ramp: '경사로', elevator: '엘리베이터', braille: '점자블록', toilet: '장애인 화장실', parking: '장애인 주차구역', other: '기타' }
  return map[type] || type || ''
}

// 지도 클릭 → 위치 정보 조회
const handleMapClick = (latLng) => {
  if (clickedMarker) {
    clickedMarker.setMap(null)
    clickedMarker = null
  }
  clickedPlace.value = null
  previewMap = null

  const lat = latLng.getLat()
  const lng = latLng.getLng()

  clickedMarker = new window.kakao.maps.Marker({ position: latLng, map })

  const geocoder = new window.kakao.maps.services.Geocoder()
  geocoder.coord2Address(lng, lat, (result, geoStatus) => {
    const addr = (geoStatus === window.kakao.maps.services.Status.OK && result[0]) ? result[0] : null

    const places = new window.kakao.maps.services.Places()
    places.keywordSearch(
      addr?.address?.address_name || '장소',
      (placeResult, placeStatus) => {
        const nearestPlace = (placeStatus === window.kakao.maps.services.Status.OK && placeResult.length) ? placeResult[0] : null

        clickedPlace.value = {
          name: nearestPlace?.place_name || '',
          address: addr?.road_address?.address_name || addr?.address?.address_name || '',
          jibun: addr?.address?.address_name || '',
          phone: nearestPlace?.phone || '',
          category: nearestPlace?.category_name || '',
          placeUrl: nearestPlace?.place_url || '',
          kakaoMapLink: `https://map.kakao.com/link/map/${encodeURIComponent(nearestPlace?.place_name || addr?.road_address?.address_name || '위치')},${lat},${lng}`,
          lat,
          lng,
        }

        nextTick(() => {
          if (previewMapContainer.value) {
            const roadview = new window.kakao.maps.Roadview(previewMapContainer.value)
            const roadviewClient = new window.kakao.maps.RoadviewClient()
            const position = new window.kakao.maps.LatLng(lat, lng)

            roadviewClient.getNearestPanoId(position, 50, (panoId) => {
              if (panoId) {
                roadview.setPanoId(panoId, position)
              } else {
                previewMapContainer.value.innerHTML = `
                  <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:13px;">
                    📷 로드뷰 정보가 없어요
                  </div>`
              }
            })
          }
        })
      },
      { location: latLng, radius: 50, size: 1, sort: 'distance' }
    )
  })
}

const clearOrigin = () => {
  originQuery.value = ''
  originResult.value = null
  originSuggestions.value = []
}

const clearDest = () => {
  destQuery.value = ''
  destResult.value = null
  destSuggestions.value = []
}

const clearFacilityQuery = () => {
  facilityQuery.value = ''
  facilityResults.value = []
  selectedFacility.value = null
  clearFacilityMarkers()
}

const clearClickedPlace = () => {
  clickedPlace.value = null
  if (clickedMarker) {
    clickedMarker.setMap(null)
    clickedMarker = null
  }
}

const setAsOrigin = (place) => {
  originResult.value = { name: place.address || place.name, lat: place.lat, lng: place.lng }
  originQuery.value = place.address || place.name
  panelMode.value = 'route'
  clearClickedPlace()
}

const setAsDest = (place) => {
  destResult.value = { name: place.address || place.name, lat: place.lat, lng: place.lng }
  destQuery.value = place.address || place.name
  panelMode.value = 'route'
  clearClickedPlace()
}

const formatDuration = (seconds) => {
  const min = Math.floor(seconds / 60)
  return min < 60 ? `${min}분` : `${Math.floor(min/60)}시간 ${min%60}분`
}

const formatDistance = (meters) => {
  return meters >= 1000 ? `${(meters/1000).toFixed(1)}km` : `${Math.round(meters)}m`
}

const formatSteps = (meters) => {
  return Math.round((meters || 0) / 0.65).toLocaleString()
}
</script>

<template>
  <div class="home">
    <div class="side-panel">
      <!-- 패널 탭 -->
      <div class="panel-tabs">
        <button :class="['panel-tab', { active: panelMode === 'route' }]" @click="panelMode = 'route'">
          길찾기
        </button>
        <button :class="['panel-tab', { active: panelMode === 'facility' }]" @click="panelMode = 'facility'">
          시설 검색
        </button>
      </div>

      <!-- 길찾기 패널 -->
      <template v-if="panelMode === 'route'">
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
            @input="onOriginInput"
          />
          <button v-if="originQuery" class="input-clear" @click="clearOrigin">✕</button>
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
            @input="onDestInput"
          />
          <button v-if="destQuery" class="input-clear" @click="clearDest">✕</button>
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

          <!-- 날씨 -->
          <div v-if="routeResult.weather" class="weather-bar">
            🌤 {{ routeResult.weather.description }} {{ routeResult.weather.temp }}°C
          </div>

          <!-- 도보: 경로 카드 목록 -->
          <template v-if="routeResult.routes">
            <div
              v-for="tab in routeTabs"
              :key="tab.key"
              :class="['route-card', { active: activeRouteTab === tab.key }]"
              @click="switchRouteTab(tab.key)"
            >
              <div class="route-card-label" :class="tab.key">
                {{ routeResult.routes[tab.key]?.label || tab.label }}
                <span v-if="tab.key === fastestRouteKey" class="fastest-badge">최단시간</span>
              </div>
              <div class="route-card-desc">{{ routeDescriptions[tab.key] }}</div>
              <div class="route-card-main">
                <span class="route-card-time">{{ formatDuration(routeResult.routes[tab.key]?.duration) }}</span>
                <span class="route-card-dist">{{ formatDistance(routeResult.routes[tab.key]?.distance) }}</span>
                <span class="route-card-steps">{{ formatSteps(routeResult.routes[tab.key]?.distance) }} 걸음</span>
              </div>
              <div class="route-card-meta">
                안전 점수 {{ ((routeResult.routes[tab.key]?.safety_score ?? 0) * 100).toFixed(0) }}점 ·
                횡단보도 {{ routeResult.routes[tab.key]?.crosswalk_count || routeResult.routes[tab.key]?.nearby?.traffic_lights?.length || 0 }}회
              </div>
              <div v-if="routeResult.routes[tab.key]?.message" class="route-card-weather-msg">
                🌧️ {{ routeResult.routes[tab.key].message }}
              </div>
              <button v-if="activeRouteTab === tab.key" class="route-card-detail-btn" @click.stop="showRouteDetail = !showRouteDetail">
                {{ showRouteDetail ? '접기' : '상세보기 >' }}
              </button>
            </div>
          </template>

          <!-- 버스/택시: 단일 경로 -->
          <template v-else-if="routeResult.route">
            <div class="route-card active">
              <div class="route-card-main">
                <span class="route-card-time">{{ formatDuration(routeResult.route.duration) }}</span>
                <span class="route-card-dist">{{ formatDistance(routeResult.route.distance) }}</span>
              </div>
              <div v-if="routeResult.taxi_fare" class="route-card-meta">
                예상 요금 {{ routeResult.taxi_fare.taxi?.toLocaleString() }}원
                <template v-if="routeResult.taxi_fare.toll">+ 통행료 {{ routeResult.taxi_fare.toll.toLocaleString() }}원</template>
              </div>
              <div v-if="routeResult.route.safety_score != null" class="route-card-meta">
                안전 점수 {{ (routeResult.route.safety_score * 100).toFixed(0) }}점
              </div>
              <div v-if="routeResult.transit_steps?.length" class="transit-steps">
                <div v-for="(step, idx) in routeResult.transit_steps" :key="idx" class="transit-step">
                  <span class="transit-step-icon">{{ transitModeIcon(step.mode) }}</span>
                  <span class="transit-step-text">
                    <template v-if="step.mode === 'WALK'">
                      도보 {{ formatDistance(step.distance) }} ({{ step.start_name }} → {{ step.end_name }})
                    </template>
                    <template v-else>
                      {{ step.route }} · {{ step.start_name }} → {{ step.end_name }}
                    </template>
                  </span>
                  <span class="transit-step-time">{{ formatDuration(step.duration) }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 위험구간 경고 -->
          <div v-if="currentNearby?.danger_zones?.length" class="danger-warning">
            <div class="danger-warning-title">⚠️ 경로 주변 위험구간 {{ currentNearby.danger_zones.length }}곳</div>
            <div v-for="dz in currentNearby.danger_zones" :key="dz.id" class="danger-zone-item">
              <span class="danger-zone-icon">{{ { danger: '⚠️', obstacle: '🚧', broken: '🔨', construction: '🏗️' }[dz.category] || '⚠️' }}</span>
              <div class="danger-zone-info">
                <span class="danger-zone-name">{{ dz.title }}</span>
                <span class="danger-zone-addr">{{ dz.address }}</span>
              </div>
            </div>
          </div>

          <!-- 주변 시설 요약 -->
          <div v-if="currentNearby" class="nearby-summary">
            <span>🚦 {{ currentNearby.traffic_lights?.length || 0 }}</span>
            <span>🏥 {{ currentNearby.hospitals?.length || 0 }}</span>
            <span>💊 {{ currentNearby.pharmacies?.length || 0 }}</span>
            <span>🏢 {{ currentNearby.welfare?.length || 0 }}</span>
          </div>


          <button v-if="auth.isLoggedIn" class="favorite-btn" @click="addFavorite">
            ⭐ 즐겨찾기 추가
          </button>
        </div>
      </template>

      <!-- 시설 검색 패널 -->
      <template v-if="panelMode === 'facility'">
        <div class="search-box">
          <input
            v-model="facilityQuery"
            type="text"
            placeholder="시설명을 검색하세요 (예: 병원, 엘리베이터)"
            @keyup.enter="searchFacility"
          />
          <button v-if="facilityQuery" class="input-clear" @click="clearFacilityQuery">✕</button>
        </div>
        <button @click="searchFacility" :disabled="facilityLoading" class="search-btn">
          {{ facilityLoading ? '검색 중...' : '시설 검색' }}
        </button>

        <!-- 검색 기록 (검색 결과가 없을 때 표시) -->
        <div v-if="facilitySearchHistory.length && !facilityResults.length && !selectedFacility" class="search-history">
          <div class="search-history-header">
            <span class="search-history-title">최근 검색</span>
            <button class="search-history-clear" @click="clearAllSearchHistory">전체 삭제</button>
          </div>
          <div class="search-history-list">
            <div v-for="keyword in facilitySearchHistory" :key="keyword" class="search-history-item">
              <span class="search-history-keyword" @click="searchFromHistory(keyword)">🔍 {{ keyword }}</span>
              <button class="search-history-remove" @click="removeSearchHistory(keyword)">✕</button>
            </div>
          </div>
        </div>

        <!-- 선택된 시설 상세 -->
        <div v-if="selectedFacility" class="facility-detail">
          <button class="facility-detail-close" @click="selectedFacility = null">✕</button>
          <h3>{{ selectedFacility.name }}</h3>
          <p v-if="selectedFacility.category" class="info-category">{{ selectedFacility.category }}</p>
          <div class="facility-detail-body">
            <p v-if="selectedFacility.address"><span class="info-icon">📍</span> {{ selectedFacility.address }}</p>
            <p v-if="selectedFacility.jibun && selectedFacility.jibun !== selectedFacility.address" class="info-jibun">(지번) {{ selectedFacility.jibun }}</p>
            <p v-if="selectedFacility.phone"><span class="info-icon">📞</span> <a :href="'tel:' + selectedFacility.phone" class="info-link">{{ selectedFacility.phone }}</a></p>
          </div>
          <a
            v-if="selectedFacility.place_url"
            :href="selectedFacility.place_url"
            target="_blank"
            rel="noopener"
            class="place-detail-link"
          >영업시간·메뉴·리뷰 등 상세정보 보기 →</a>
          <div class="facility-actions">
            <button class="action-btn" @click="setAsOrigin(selectedFacility)">출발지로 설정</button>
            <button class="action-btn action-btn-primary" @click="setAsDest(selectedFacility)">목적지로 설정</button>
          </div>
        </div>

        <!-- 검색 결과 목록 -->
        <div v-if="facilityResults.length && !selectedFacility" class="facility-list">
          <div
            v-for="(f, i) in facilityResults"
            :key="i"
            class="facility-item"
            @click="selectFacility(f)"
          >
            <div class="facility-item-name">{{ f.name }}</div>
            <p v-if="f.category" class="info-category">{{ f.category }}</p>
            <p class="facility-item-sub"><span class="info-icon">📍</span> {{ f.address }}</p>
            <p v-if="f.jibun && f.jibun !== f.address" class="info-jibun">(지번) {{ f.jibun }}</p>
            <p v-if="f.phone" class="facility-item-sub"><span class="info-icon">📞</span> {{ f.phone }}</p>
          </div>
        </div>

        <!-- 검색 기록 (검색 결과 아래) -->
        <div v-if="facilitySearchHistory.length && facilityResults.length && !selectedFacility" class="search-history below">
          <div class="search-history-header">
            <span class="search-history-title">최근 검색</span>
            <button class="search-history-clear" @click="clearAllSearchHistory">전체 삭제</button>
          </div>
          <div class="search-history-list">
            <div v-for="keyword in facilitySearchHistory" :key="keyword" class="search-history-item">
              <span class="search-history-keyword" @click="searchFromHistory(keyword)">🔍 {{ keyword }}</span>
              <button class="search-history-remove" @click="removeSearchHistory(keyword)">✕</button>
            </div>
          </div>
        </div>

        <p v-if="!facilityLoading && facilityResults.length === 0 && facilityQuery" class="no-result">
          검색 결과가 없습니다.
        </p>
      </template>

      <!-- 지도 클릭 위치 정보 -->
      <div v-if="clickedPlace" class="clicked-place">
        <div class="clicked-place-top">
          <h4 v-if="clickedPlace.name">{{ clickedPlace.name }}</h4>
          <h4 v-else>선택한 위치</h4>
          <button class="clicked-place-close" @click="clearClickedPlace">✕</button>
        </div>

        <p v-if="clickedPlace.category" class="clicked-category">{{ clickedPlace.category }}</p>

        <div ref="previewMapContainer" class="clicked-place-img"></div>

        <div class="facility-detail-body">
          <p>📍 {{ clickedPlace.address }}</p>
          <p v-if="clickedPlace.jibun && clickedPlace.jibun !== clickedPlace.address" class="jibun">
            (지번) {{ clickedPlace.jibun }}
          </p>
          <p v-if="clickedPlace.phone">📞 <a :href="'tel:' + clickedPlace.phone">{{ clickedPlace.phone }}</a></p>
        </div>

        <a
          :href="clickedPlace.placeUrl || clickedPlace.kakaoMapLink"
          target="_blank"
          rel="noopener"
          class="place-detail-link"
        >
          영업시간·메뉴·리뷰 등 상세정보 보기 →
        </a>

        <div class="facility-actions">
          <button class="action-btn" @click="setAsOrigin(clickedPlace)">출발지로 설정</button>
          <button class="action-btn action-btn-primary" @click="setAsDest(clickedPlace)">목적지로 설정</button>
        </div>
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

      <!-- 우측 상단 토글 버튼 (SOS 아래) -->
      <div class="side-toggle-bar">
        <button
          :class="['side-toggle-btn', { active: trafficActive }]"
          @click="toggleTraffic"
        >
          🚦 교통정보
        </button>
        <button
          :class="['side-toggle-btn', { active: congestionActive }]"
          @click="toggleCongestion()"
        >
          🧍 인구밀도
        </button>
      </div>

      <div v-if="congestionActive" class="congestion-box">
        <button class="congestion-close" @click="toggleCongestion()">✕</button>
        <div v-if="congestionLoading">혼잡도 조회 중...</div>
        <template v-else-if="congestionInfo">
          <strong>{{ congestionInfo.area }}</strong>
          <div class="congestion-level" :style="{ color: congestionLevelColor(congestionInfo.level) }">{{ congestionInfo.level }}</div>
          <div class="congestion-msg">{{ congestionInfo.message }}</div>
        </template>
      </div>

      <div ref="mapContainer" class="map"></div>

      <!-- 경로 상세 슬라이드 패널 -->
      <Transition name="slide-panel">
        <div v-if="showRouteDetail && currentNearby" class="detail-slide-panel">
          <div class="detail-slide-header">
            <h3>{{ routeResult?.routes?.[activeRouteTab]?.label || '경로' }} 상세</h3>
            <button class="detail-slide-close" @click="showRouteDetail = false">✕</button>
          </div>
          <div class="detail-slide-summary">
            <span v-if="routeResult?.routes">
              {{ formatDuration(routeResult.routes[activeRouteTab]?.duration) }} · {{ formatDistance(routeResult.routes[activeRouteTab]?.distance) }} · {{ formatSteps(routeResult.routes[activeRouteTab]?.distance) }} 걸음
            </span>
            <span>횡단보도 {{ currentNearby.traffic_lights?.length || 0 }}회</span>
          </div>
          <div class="detail-slide-body">
            <div v-if="currentNearby.traffic_lights?.length" class="detail-group">
              <h4>🚦 상세 경로</h4>
              <div v-for="(tl, i) in currentNearby.traffic_lights" :key="'tl'+i" class="detail-item detail-item-vertical" :class="{ 'detail-item-border': i > 0 }">
                <span class="detail-item-name">{{ tl.description || tl.road_nm }}</span>
                <span v-if="tl.has_audio || tl.has_remndr" class="detail-badges">
                  <span v-if="tl.has_audio" class="audio-badge">음향신호기</span>
                  <span v-if="tl.has_remndr" class="remndr-badge">보행 잔여 시간</span>
                </span>
                <span v-if="remainingSignalSeconds(tl) != null" class="realtime-signal">
                  🔴 실시간 보행신호 {{ remainingSignalSeconds(tl) }}초 남음
                </span>
              </div>
            </div>
            <div v-if="currentNearby.hospitals?.length" class="detail-group">
              <h4 class="detail-group-toggle" @click="toggleDetailGroup('hospitals')">
                <span>🏥 병원 ({{ currentNearby.hospitals.length }})</span>
                <span class="detail-group-caret">{{ detailGroupOpen.hospitals ? '▲' : '▼' }}</span>
              </h4>
              <template v-if="detailGroupOpen.hospitals">
                <div v-for="(h, i) in currentNearby.hospitals" :key="'h'+i" class="detail-item">
                  <span class="detail-item-name">{{ h.name }}</span>
                  <span v-if="h.phone" class="detail-item-sub">{{ h.phone }}</span>
                </div>
              </template>
            </div>
            <div v-if="currentNearby.pharmacies?.length" class="detail-group">
              <h4 class="detail-group-toggle" @click="toggleDetailGroup('pharmacies')">
                <span>💊 약국 ({{ currentNearby.pharmacies.length }})</span>
                <span class="detail-group-caret">{{ detailGroupOpen.pharmacies ? '▲' : '▼' }}</span>
              </h4>
              <template v-if="detailGroupOpen.pharmacies">
                <div v-for="(p, i) in currentNearby.pharmacies" :key="'p'+i" class="detail-item">
                  <span class="detail-item-name">{{ p.name }}</span>
                  <span v-if="p.phone" class="detail-item-sub">{{ p.phone }}</span>
                </div>
              </template>
            </div>
            <div v-if="currentNearby.welfare?.length" class="detail-group">
              <h4 class="detail-group-toggle" @click="toggleDetailGroup('welfare')">
                <span>🏢 복지시설 ({{ currentNearby.welfare.length }})</span>
                <span class="detail-group-caret">{{ detailGroupOpen.welfare ? '▲' : '▼' }}</span>
              </h4>
              <template v-if="detailGroupOpen.welfare">
                <div v-for="(w, i) in currentNearby.welfare" :key="'w'+i" class="detail-item">
                  <span class="detail-item-name">{{ w.name }}</span>
                  <span v-if="w.phone" class="detail-item-sub">{{ w.phone }}</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </Transition>

      <!-- SOS 버튼 (오른쪽 상단) -->
      <button @click="sendSOS" class="sos-btn" title="SOS">SOS</button>

      <!-- 지도 컨트롤 버튼 (오른쪽 하단) -->
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
/* 패널 탭 */
.panel-tabs {
  display: flex;
  gap: 0;
  border: 1px solid #ddd;
  border-radius: 10px;
  overflow: hidden;
}
.panel-tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: white;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 600;
  color: #666;
  transition: all 0.2s;
}
.panel-tab.active {
  background: #2eb872;
  color: white;
}
h2 {
  font-size: calc(var(--base-font-size, 16px) + 2px);
  color: #2eb872;
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
  background: #2eb872;
  color: white;
  border-color: #2eb872;
}
.search-box {
  position: relative;
}
.search-box input {
  width: 100%;
  padding: 10px 32px 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  outline: none;
  box-sizing: border-box;
}
.search-box input:focus {
  border-color: #2eb872;
}
.input-clear {
  position: absolute;
  right: 10px;
  top: 20px;
  transform: translateY(-50%);
  background: #bbb;
  border: none;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  font-size: 12px;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  padding: 0;
  z-index: 2;
}
.input-clear:hover {
  background: #888;
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
  background-color: #e6f7ee;
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
  background-color: #2eb872;
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
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 날씨 바 */
.weather-bar {
  padding: 8px 12px;
  background: #e6f7ee;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
/* 경로 카드 */
.route-card {
  padding: 14px;
  background: #f8f9fa;
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.route-card:hover {
  background: #e6f7ee;
}
.route-card.active {
  background: white;
  border-color: #2eb872;
  box-shadow: 0 2px 8px rgba(46,184,114,0.15);
}
.route-card-label {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 700;
  color: #2eb872;
}
.route-card-label.stair_free { color: #805ad5; }
.route-card-label.main_road { color: #3366FF; }
.route-card-label.weather { color: #e65100; }
.fastest-badge {
  display: inline-block;
  font-size: calc(var(--base-font-size, 16px) - 6px);
  font-weight: 700;
  color: #fff;
  background: #ff7043;
  border-radius: 8px;
  padding: 1px 6px;
  margin-left: 4px;
  vertical-align: middle;
}
.route-card-desc {
  font-size: calc(var(--base-font-size, 16px) - 5px);
  color: #aaa;
}
.route-card-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.route-card-time {
  font-size: calc(var(--base-font-size, 16px) + 4px);
  font-weight: 800;
  color: #222;
}
.route-card-dist {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 600;
  color: #555;
}
.route-card-steps {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 600;
  color: #555;
}
.route-card-meta {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #999;
}
.transit-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #eee;
}
.transit-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #444;
}
.transit-step-icon {
  flex-shrink: 0;
}
.transit-step-text {
  flex: 1;
}
.transit-step-time {
  color: #999;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.route-card-weather-msg {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #e65100;
  background: #fff3e0;
  padding: 4px 8px;
  border-radius: 6px;
  margin-top: 2px;
}
.route-card-detail-btn {
  align-self: flex-start;
  background: none;
  border: none;
  color: #2eb872;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  cursor: pointer;
  padding: 2px 0;
}
.route-card-detail-btn:hover {
  text-decoration: underline;
}

/* 위험구간 경고 */
.danger-warning {
  background: #fff0f0;
  border: 1.5px solid #e53e3e;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.danger-warning-title {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 700;
  color: #e53e3e;
}
.danger-zone-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-top: 1px solid #fdd;
}
.danger-zone-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.danger-zone-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.danger-zone-name {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  color: #333;
}
.danger-zone-addr {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #999;
}

/* 주변 시설 요약 */
.nearby-summary {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
}
.favorite-btn {
  padding: 10px;
  background: white;
  border: 1px solid #2eb872;
  color: #2eb872;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: bold;
}

/* 시설 검색 결과 목록 */
.facility-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 400px;
  overflow-y: auto;
}
.facility-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}
.facility-item:hover {
  background: #e6f7ee;
}
.facility-item-name {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 600;
  color: #222;
}
.facility-item-address {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #888;
  margin-top: 2px;
}
.facility-type-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #2eb872;
  color: white;
  font-size: calc(var(--base-font-size, 16px) - 5px);
  font-weight: 600;
}
.facility-type-badge.small {
  font-size: calc(var(--base-font-size, 16px) - 6px);
  padding: 1px 6px;
}
.no-result {
  text-align: center;
  color: #999;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  padding: 20px 0;
}

/* 시설 검색 기록 */
.search-history {
  background: #f9f9f9;
  border-radius: 10px;
  padding: 12px;
}
.search-history.below {
  margin-top: 4px;
}
.search-history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.search-history-title {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  color: #555;
}
.search-history-clear {
  background: none;
  border: none;
  color: #999;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  cursor: pointer;
}
.search-history-clear:hover {
  color: #e53e3e;
}
.search-history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.search-history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 4px;
  border-radius: 6px;
}
.search-history-item:hover {
  background: #e6f7ee;
}
.search-history-keyword {
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #444;
}
.search-history-remove {
  background: none;
  border: none;
  color: #ccc;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
}
.search-history-remove:hover {
  color: #999;
}
.facility-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.facility-item-dist {
  font-size: calc(var(--base-font-size, 16px) - 5px);
  color: #2eb872;
  font-weight: 600;
}
.facility-item-phone {
  font-size: calc(var(--base-font-size, 16px) - 5px);
  color: #888;
}
.detail-ext-link {
  color: #2eb872;
  text-decoration: none;
  font-weight: 600;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.detail-ext-link:hover {
  text-decoration: underline;
}
.facility-item-category {
  font-size: calc(var(--base-font-size, 16px) - 5px);
  color: #2eb872;
  font-weight: 500;
}
.facility-item-phone {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #666;
  margin-top: 2px;
}
.facility-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.facility-category-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  background: #e6f7ee;
  color: #2eb872;
  font-size: calc(var(--base-font-size, 16px) - 5px);
  font-weight: 500;
}

/* 시설 상세 */
.facility-detail {
  position: relative;
  background: #e6f7ee;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.facility-detail h3 {
  font-size: calc(var(--base-font-size, 16px) + 1px);
  font-weight: 700;
  color: #222;
  margin: 0;
  padding-right: 24px;
}
.facility-detail-close {
  position: absolute;
  top: 10px;
  right: 12px;
  background: rgba(255,255,255,0.9);
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #666;
  z-index: 10;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
}
.facility-detail-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.facility-detail-body p {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
}
.facility-detail-body a {
  color: #2eb872;
  text-decoration: none;
}
.status-open { color: #38a169; font-weight: 600; }
.status-closed { color: #e53e3e; font-weight: 600; }

.facility-actions {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.action-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid #2eb872;
  border-radius: 8px;
  background: white;
  color: #2eb872;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.action-btn:hover {
  background: #e6f7ee;
}
.action-btn-primary {
  background: #2eb872;
  color: white;
}
.action-btn-primary:hover {
  background: #259a60;
}
.sos-btn {
  position: absolute;
  top: 12px;  /* 60px → 12px */
  right: 16px;
  width: 48px;
  height: 48px;
  background: #e53e3e;
  color: white;
  font-weight: 700;
  font-size: 13px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  z-index: 10;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.sos-btn:hover {
  background: #c53030;
}
.side-toggle-bar {
  position: absolute;
  top: 68px;
  right: 16px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.side-toggle-btn {
  padding: 8px 12px;
  background: white;
  border: 1.5px solid #ddd;
  border-radius: 20px;
  cursor: pointer;
  white-space: nowrap;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.side-toggle-btn.active {
  background: #2eb872;
  border-color: #2eb872;
  color: white;
}

/* 지도 클릭 위치 */
.clicked-place {
  position: relative;
  background: #fff8e1;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.clicked-place-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.clicked-place-top h4 {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px));
  color: #333;
  font-weight: 700;
  flex: 1;
}
.clicked-place-close {
  background: #eee;
  border: none;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.clicked-place-close:hover {
  background: #ddd;
  color: #333;
}
.clicked-place p {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
}
.clicked-place .jibun {
  color: #999;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.clicked-place-img {
  width: 100%;
  height: 180px;
  border-radius: 8px;
  background: #eee;
  overflow: hidden;
}
.place-detail-link {
  display: block;
  padding: 10px;
  background: #fee500;
  color: #3c1e1e;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 600;
  text-decoration: none;
  text-align: center;
  transition: background 0.15s;
}
.place-detail-link:hover {
  background: #fdd835;
}

/* 통일 정보 스타일 */
p.info-category {
  font-size: calc(var(--base-font-size, 16px) - 4px) !important;
  color: #999 !important;
  margin: 0 !important;
}
p.info-jibun {
  font-size: calc(var(--base-font-size, 16px) - 5px) !important;
  color: #aaa !important;
  margin: -1px 0 0 20px !important;
}
.info-icon {
  opacity: 0.7;
}
.info-link {
  color: #2eb872;
  text-decoration: none;
}
.info-link:hover {
  text-decoration: underline;
}
.facility-item-sub {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #666;
  margin: 1px 0 0;
}

.clicked-category {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #2eb872;
  font-weight: 500;
}
.clicked-links {
  display: flex;
  gap: 8px;
}
.clicked-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 12px;
  background: #fee500;
  color: #3c1e1e;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s;
}
.clicked-link-btn:hover {
  background: #fdd835;
}

/* 교통약자 유형 */
.user-type-bar, .speed-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bar-label {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  color: #555;
}
.user-type-options {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.type-btn {
  padding: 5px 12px;
  border: 1px solid #ddd;
  border-radius: 16px;
  background: white;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #666;
}
.type-btn.active {
  background: #2eb872;
  color: white;
  border-color: #2eb872;
}
.speed-slider {
  width: 100%;
  accent-color: #2eb872;
}
.detail-toggle {
  padding: 8px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
  text-align: center;
}
.detail-toggle:hover {
  background: #f9f9f9;
}
.route-detail-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}
.detail-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-group h4 {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-weight: 700;
  color: #333;
  margin: 0;
}
.detail-group-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.detail-group-caret {
  font-size: calc(var(--base-font-size, 16px) - 5px);
  color: #999;
}
.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 12px;
  background: white;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  transition: all 0.15s;
  gap: 10px;
}
.detail-item-vertical {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.detail-item-border {
  border-top: 1px solid #eee;
  border-radius: 0;
}
.detail-item.clickable {
  cursor: pointer;
}
.detail-item.clickable:hover {
  background: #e6f7ee;
}
.detail-item.selected {
  background: #FF6B00;
  color: white;
}
.detail-item.selected .detail-item-name {
  color: white;
}
.detail-item.selected .detail-item-type {
  color: rgba(255,255,255,0.8);
}
.detail-item-name {
  color: #333;
}
.detail-item-type, .detail-item-sub {
  color: #888;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.detail-item-name {
  flex: 1;
  min-width: 0;
  word-break: keep-all;
  overflow-wrap: break-word;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  line-height: 1.4;
}
.detail-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.audio-badge {
  background: #2eb872;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 600;
  white-space: nowrap;
}
.remndr-badge {
  background: #3366FF;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 600;
  white-space: nowrap;
}
.realtime-signal {
  display: block;
  margin-top: 4px;
  color: #e53e3e;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 700;
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
.congestion-box {
  position: absolute;
  top: 168px;
  right: 16px;
  width: 220px;
  z-index: 10;
  background: white;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.congestion-close {
  position: absolute;
  top: 8px;
  right: 10px;
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.congestion-level {
  font-weight: bold;
  margin-bottom: 4px;
}
.congestion-msg {
  color: #666;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  line-height: 1.5;
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

/* 경로 상세 슬라이드 패널 */
.detail-slide-panel {
  position: absolute;
  top: 0;
  left: 0;
  width: 440px;
  height: 100%;
  background: white;
  z-index: 20;
  box-shadow: 4px 0 16px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-slide-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.detail-slide-header h3 {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px) + 1px);
  font-weight: 700;
  color: #222;
}
.detail-slide-close {
  background: #f0f0f0;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 16px;
  color: #666;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.detail-slide-close:hover {
  background: #ddd;
}
.detail-slide-summary {
  padding: 12px 20px;
  background: #f8f9fa;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
  display: flex;
  gap: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid #eee;
}
.detail-slide-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.slide-panel-enter-active {
  transition: transform 0.3s ease;
}
.slide-panel-leave-active {
  transition: none;
}
.slide-panel-enter-from {
  transform: translateX(-100%);
}
.slide-panel-leave-to {
  display: none;
}

@media (max-width: 768px) {
  .detail-slide-panel {
    width: 100%;
  }
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
  background: #e6f7ee;
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
  position: relative;
  background: white;
  border-radius: 14px;
  padding: 14px 16px;
  width: 280px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  gap: 8px;
  line-height: 1.5;
  font-family: 'Poppins', 'Noto Sans KR', sans-serif;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.marker-overlay-close {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #f5f5f5;
  border: none;
  font-size: 14px;
  color: #888;
  cursor: pointer;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  padding: 0;
  line-height: 1;
}
.marker-overlay-close:hover {
  background: #e0e0e0;
  color: #333;
}
.marker-overlay-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 20px;
}
.marker-overlay-icon-big {
  font-size: 28px;
  flex-shrink: 0;
}
.marker-overlay-head-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}
.marker-overlay-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #222;
  word-break: keep-all;
  overflow-wrap: break-word;
  white-space: normal;
  line-height: 1.4;
}
.marker-overlay-label {
  font-size: 12px;
  font-weight: 600;
}
.marker-overlay-row {
  margin: 0;
  font-size: 12px;
  color: #555;
  word-break: keep-all;
  overflow-wrap: break-word;
  white-space: normal;
  line-height: 1.4;
}
.marker-overlay-phone {
  color: #2eb872;
  text-decoration: none;
  font-weight: 500;
}
.marker-overlay-phone:hover {
  text-decoration: underline;
}
.marker-overlay-detail-btn {
  display: block;
  margin-top: 2px;
  padding: 8px 10px;
  background: #fee500;
  color: #3c1e1e;
  text-decoration: none;
  font-weight: 700;
  font-size: 13px;
  text-align: center;
  border-radius: 8px;
}
.marker-overlay-detail-btn:hover {
  background: #fdd835;
}
.marker-overlay-arrow {
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 12px solid white;
  margin: 0 auto;
  filter: drop-shadow(0 2px 3px rgba(0,0,0,0.12));
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
  background: #2eb872;
}
.route-marker-dest {
  background: #e53e3e;
}

@media (max-width: 768px) {
  .marker-overlay-inner {
    width: 240px;
    padding: 12px 14px;
  }
  .marker-overlay-icon-big {
    font-size: 22px;
  }
  .marker-overlay-name {
    font-size: 14px;
  }
  .marker-overlay-row {
    font-size: 12px;
  }
  .route-marker-label {
    font-size: 11px;
    padding: 2px 8px;
  }
}

/* 로드뷰 컨트롤 축소 */
.clicked-place-img .rv_compass {
  transform: scale(0.6) !important;
  transform-origin: top right !important;
}
.clicked-place-img .rv_control_compass {
  transform: scale(0.6) !important;
  transform-origin: top right !important;
}
.clicked-place-img .rv_control_zoom {
  transform: scale(0.7) !important;
  transform-origin: bottom right !important;
}
</style>