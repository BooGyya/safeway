<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { routeAPI } from '@/api/routes'
import { infraAPI } from '@/api/infra'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { useMapStore } from '@/stores/map'
import { authAPI } from '@/api/auth'

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
  { key: 'elevator', label: '엘리베이터', icon: '🛗', color: '#2eb872' },
  { key: 'support_center', label: '지원센터', icon: '🤝', color: '#dd6b20' },
]
const activeCategories = ref(new Set())
let activeOverlay = null
let pinnedOverlay = null

// 패널 모드
const panelMode = ref('route')

// 시설 검색 관련
const facilityQuery = ref('')
const facilityResults = ref([])
const facilityLoading = ref(false)
const selectedFacility = ref(null)
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
const selectedDetailFacility = ref(null)
let focusedMarker = null

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
      user_type: selectedUserType.value,
      walk_speed: walkSpeed.value,
    })
    routeResult.value = data
    drawRoute(data)
    fetchNearbyFacilities(data.route)
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

// 시설 검색
const searchFacility = async () => {
  if (!facilityQuery.value.trim()) return
  facilityLoading.value = true
  facilityResults.value = []
  selectedFacility.value = null
  try {
    const [facilityRes, kakaoRes] = await Promise.allSettled([
      infraAPI.searchFacilities(facilityQuery.value),
      routeAPI.searchAddress(facilityQuery.value),
    ])
    const dbResults = facilityRes.status === 'fulfilled'
      ? (Array.isArray(facilityRes.value.data) ? facilityRes.value.data : [])
      : []
    const kakaoResults = kakaoRes.status === 'fulfilled'
      ? (Array.isArray(kakaoRes.value.data) ? kakaoRes.value.data : []).map(p => ({
          ...p,
          source: 'kakao',
        }))
      : []
    facilityResults.value = [...dbResults, ...kakaoResults]
    clearFacilityMarkers()
    facilityResults.value.forEach(f => {
      if (!f.lat || !f.lng) return
      const marker = new window.kakao.maps.Marker({
        position: new window.kakao.maps.LatLng(f.lat, f.lng),
        map,
      })
      window.kakao.maps.event.addListener(marker, 'click', () => selectFacility(f))
      facilityMarkers.push(marker)
    })
    if (facilityResults.value.length > 0) {
      const bounds = new window.kakao.maps.LatLngBounds()
      facilityResults.value.forEach(f => {
        if (f.lat && f.lng) bounds.extend(new window.kakao.maps.LatLng(f.lat, f.lng))
      })
      map.setBounds(bounds)
    }
  } catch {
    facilityResults.value = []
  } finally {
    facilityLoading.value = false
  }
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
            @keyup="searchAddress(originQuery, 'origin')"
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
            @keyup="searchAddress(destQuery, 'dest')"
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

          <button class="detail-toggle" @click="showRouteDetail = !showRouteDetail">
            {{ showRouteDetail ? '상세 접기 ▲' : '경로 상세보기 ▼' }}
          </button>

          <div v-if="showRouteDetail && routeResult.nearby" class="route-detail-section">
            <div v-if="routeResult.nearby.facilities?.length" class="detail-group">
              <h4>♿ 주변 편의시설</h4>
              <div
                v-for="f in routeResult.nearby.facilities"
                :key="f.id"
                :class="['detail-item', 'clickable', { selected: selectedDetailFacility?.id === f.id }]"
                @click="focusFacilityOnMap(f)"
              >
                <span class="detail-item-name">{{ f.name }}</span>
                <span v-if="f.facility_type && f.facility_type !== 'other'" class="detail-item-type">{{ facilityTypeLabel(f.facility_type) }}</span>
              </div>
            </div>
            <div v-if="routeResult.nearby.traffic_lights?.length" class="detail-group">
              <h4>🚦 주변 신호등</h4>
              <div v-for="tl in routeResult.nearby.traffic_lights" :key="tl.id" class="detail-item">
                <span class="detail-item-name">{{ tl.road_nm || tl.name }}</span>
                <span v-if="tl.has_audio" class="audio-badge">음향</span>
              </div>
            </div>
            <div v-if="routeResult.nearby.support_centers?.length" class="detail-group">
              <h4>🏥 이동지원센터</h4>
              <div v-for="sc in routeResult.nearby.support_centers" :key="sc.id" class="detail-item">
                <span class="detail-item-name">{{ sc.name }}</span>
                <span class="detail-item-sub">{{ sc.phone }}</span>
              </div>
            </div>

            <div v-if="nearbyOriginFacilities.length" class="detail-group">
              <h4>📍 출발지 근처 시설</h4>
              <div v-for="(f, i) in nearbyOriginFacilities" :key="'o'+i" class="detail-item">
                <span class="detail-item-name">{{ f.name }}</span>
                <span class="detail-item-type">{{ f.type }}</span>
              </div>
            </div>
            <div v-if="nearbyDestFacilities.length" class="detail-group">
              <h4>🏁 도착지 근처 시설</h4>
              <div v-for="(f, i) in nearbyDestFacilities" :key="'d'+i" class="detail-item">
                <span class="detail-item-name">{{ f.name }}</span>
                <span class="detail-item-type">{{ f.type }}</span>
              </div>
            </div>
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

        <!-- 선택된 시설 상세 -->
        <div v-if="selectedFacility" class="facility-detail">
          <button class="facility-detail-close" @click="selectedFacility = null">✕</button>
          <h3>{{ selectedFacility.name }}</h3>
          <span v-if="selectedFacility.facility_type" class="facility-type-badge">
            {{ facilityTypeLabel(selectedFacility.facility_type) }}
          </span>
          <div class="facility-detail-body">
            <p v-if="selectedFacility.address">📍 {{ selectedFacility.address }}</p>
            <p v-if="selectedFacility.sido">📌 {{ selectedFacility.sido }} {{ selectedFacility.sigungu }}</p>
            <p v-if="selectedFacility.phone">📞 <a :href="'tel:' + selectedFacility.phone">{{ selectedFacility.phone }}</a></p>
            <p v-if="selectedFacility.is_available !== undefined">
              상태: <span :class="selectedFacility.is_available ? 'status-open' : 'status-closed'">
                {{ selectedFacility.is_available ? '이용 가능' : '이용 불가' }}
              </span>
            </p>
          </div>
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
            <div class="facility-item-address">{{ f.address }}</div>
            <span v-if="f.facility_type" class="facility-type-badge small">
              {{ facilityTypeLabel(f.facility_type) }}
            </span>
          </div>
        </div>

        <p v-if="!facilityLoading && facilityResults.length === 0 && facilityQuery" class="no-result">
          검색 결과가 없습니다.
        </p>
      </template>

      <!-- 지도 클릭 위치 정보 -->
      <div v-if="clickedPlace" class="clicked-place">
        <button class="facility-detail-close" @click="clearClickedPlace">✕</button>

        <div ref="previewMapContainer" class="clicked-place-img"></div>

        <h4 v-if="clickedPlace.name">{{ clickedPlace.name }}</h4>
        <h4 v-else>선택한 위치</h4>

        <p v-if="clickedPlace.category" class="clicked-category">{{ clickedPlace.category }}</p>

        <div class="facility-detail-body">
          <p>📍 {{ clickedPlace.address }}</p>
          <p v-if="clickedPlace.jibun && clickedPlace.jibun !== clickedPlace.address" class="jibun">
            (지번) {{ clickedPlace.jibun }}
          </p>
          <p v-if="clickedPlace.phone">📞 <a :href="'tel:' + clickedPlace.phone">{{ clickedPlace.phone }}</a></p>
        </div>

        <div class="clicked-links">
          <a
            v-if="clickedPlace.placeUrl"
            :href="clickedPlace.placeUrl"
            target="_blank"
            rel="noopener"
            class="clicked-link-btn"
          >
            카카오맵에서 보기
          </a>
          <a
            v-else
            :href="clickedPlace.kakaoMapLink"
            target="_blank"
            rel="noopener"
            class="clicked-link-btn"
          >
            카카오맵에서 보기
          </a>
        </div>

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

      <div ref="mapContainer" class="map"></div>

      <!-- 지도 컨트롤 버튼 -->
      <div class="map-controls">
        <button @click="sendSOS" class="control-btn sos-btn" title="SOS">
            SOS
        </button>
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
  background: #e6f7ee;
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
.safety { color: #2eb872; }
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
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #999;
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
  background: #e53e3e !important;
  color: white;
  font-weight: 700;
  font-size: 13px;
  border: none !important;
}
.sos-btn:hover {
  background: #c53030 !important;
}

/* 지도 클릭 위치 */
.clicked-place {
  position: relative;
  background: #fff8e1;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.clicked-place h4 {
  margin: 0;
  font-size: calc(var(--base-font-size, 16px) - 1px);
  color: #333;
  font-weight: 700;
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
  height: 120px;
  border-radius: 8px;
  background: #eee;
  overflow: hidden;
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
.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: white;
  border-radius: 6px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  transition: all 0.15s;
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
.audio-badge {
  background: #2eb872;
  color: white;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 5px);
  font-weight: 600;
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
  color: #2eb872;
  text-decoration: none;
}
.marker-overlay-phone:hover {
  text-decoration: underline;
}
.marker-overlay-link {
  color: #2eb872;
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
  background: #2eb872;
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