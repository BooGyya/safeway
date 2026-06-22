from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import requests
import os
import math

from .models import Route, RouteFavorite, RouteHistory
from .serializers import RouteSerializer, RouteFavoriteSerializer, RouteHistorySerializer
from infrastructure.models import TrafficLight, Facility, SupportCenter

def get_distance(lat1, lng1, lat2, lng2):
    """두 좌표 사이 거리 계산 (Haversine formula, 단위: m)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=1.0):
    """TMAP 보행자 경로 탐색"""
    API_KEY = os.getenv('TMAP_API_KEY')
    url = 'https://apis.openapi.sk.com/tmap/routes/pedestrian'

    headers = {
        'appKey': API_KEY,
        'Content-Type': 'application/json',
    }
    # 보행속도 m/s → km/h 변환 (TMAP은 km/h 단위)
    speed_kmh = max(1, int(speed * 3.6))

    body = {
        'startX': str(origin_lng),
        'startY': str(origin_lat),
        'endX': str(dest_lng),
        'endY': str(dest_lat),
        'reqCoordType': 'WGS84GEO',
        'resCoordType': 'WGS84GEO',
        'startName': '출발지',
        'endName': '목적지',
        'speed': speed_kmh,
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        return response.json()
    except Exception as e:
        print(f"TMAP 경로 탐색 오류: {e}")
        return None


def calculate_safety_score(waypoints, user_type):
    """경로 안전도 점수 계산"""
    if not waypoints:
        return 0.5

    score = 1.0
    radius = 0.001  # 약 100m

    for point in waypoints:
        lat, lng = point.get('lat'), point.get('lng')
        if not lat or not lng:
            continue

        # 주변 신호등 조회
        lights = TrafficLight.objects.filter(
            lat__range=(lat - radius, lat + radius),
            lng__range=(lng - radius, lng + radius),
            is_operating=True
        )

        for light in lights:
            green_time = light.get_pedestrian_green_time()

            # 사용자 유형별 보행속도 (m/s)
            speed_map = {
                'wheelchair': 0.5,
                'elderly': 0.7,
                'disabled': 0.6,
                'pregnant': 0.8,
                'normal': 1.0,
            }
            speed = speed_map.get(user_type, 1.0)

            # 횡단보도 거리 (약 10m 가정)
            crossing_dist = 10
            time_needed = crossing_dist / speed

            if green_time and green_time < time_needed:
                score -= 0.1

            # 음향신호기 없으면 시각장애인에게 불리
            if user_type == 'disabled' and not light.has_audio:
                score -= 0.05

    return max(0.0, min(1.0, score))


def get_weather_info(lat, lng):
    """날씨 정보 조회"""
    API_KEY = os.getenv('WEATHER_API_KEY')
    url = 'https://api.openweathermap.org/data/2.5/weather'
    params = {
        'lat': lat,
        'lon': lng,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'kr',
    }
    try:
        response = requests.get(url, params=params, timeout=3)
        data = response.json()
        return {
            'weather': data['weather'][0]['main'],
            'description': data['weather'][0]['description'],
            'temp': data['main']['temp'],
            'wind_speed': data['wind']['speed'],
        }
    except Exception:
        return None


# 경로 탐색
@api_view(['POST'])
@permission_classes([AllowAny])
def search_route(request):
    origin_lat = request.data.get('origin_lat')
    origin_lng = request.data.get('origin_lng')
    origin_name = request.data.get('origin_name', '출발지')
    dest_lat = request.data.get('dest_lat')
    dest_lng = request.data.get('dest_lng')
    dest_name = request.data.get('dest_name', '목적지')

    if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
        return Response(
            {'error': '출발지와 목적지 좌표를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    origin_lat, origin_lng = float(origin_lat), float(origin_lng)
    dest_lat, dest_lng = float(dest_lat), float(dest_lng)

    # 카카오맵 경로 탐색
    user_speed = request.user.walk_speed if request.user.is_authenticated else 1.0
    tmap_data = get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed)
    
    waypoints = []
    distance = 0
    duration = 0

    if tmap_data and tmap_data.get('features'):
        for feature in tmap_data['features']:
            geometry = feature.get('geometry', {})
            properties = feature.get('properties', {})

            # 거리/시간 추출
            if properties.get('totalDistance'):
                distance = properties['totalDistance']
            if properties.get('totalTime'):
                duration = properties['totalTime']

            # 경유지 추출
            if geometry.get('type') == 'LineString':
                for coord in geometry.get('coordinates', []):
                    waypoints.append({
                        'lat': coord[1],
                        'lng': coord[0],
                    })

    # 날씨 정보 조회
    weather = get_weather_info(origin_lat, origin_lng)
    weather_applied = False

    if weather:
        bad_weather = ['Rain', 'Snow', 'Thunderstorm', 'Drizzle']
        if weather['weather'] in bad_weather or weather['wind_speed'] > 10:
            weather_applied = True
            duration = int(duration * 1.2)  # 20% 추가 소요

    # 안전도 점수 계산
    user_type = request.user.user_type if request.user.is_authenticated else 'normal'
    safety_score = calculate_safety_score(waypoints, user_type)

    # 경로 저장
    if request.user.is_authenticated:
        route = Route.objects.create(
            user=request.user,
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_name=dest_name,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            distance=distance,
            duration=duration,
            safety_score=safety_score,
            waypoints=waypoints,
            weather_applied=weather_applied,
        )
        RouteHistory.objects.create(user=request.user, route=route)
        route_data = RouteSerializer(route).data
    else:
        route_data = {
            'origin_name': origin_name,
            'origin_lat': origin_lat,
            'origin_lng': origin_lng,
            'dest_name': dest_name,
            'dest_lat': dest_lat,
            'dest_lng': dest_lng,
            'distance': distance,
            'duration': duration,
            'safety_score': safety_score,
            'waypoints': waypoints,
            'weather_applied': weather_applied,
        }
    # 경로 주변 편의시설 정보 수집
    nearby = {
        'traffic_lights': [],
        'facilities': [],
        'support_centers': [],
    }

    if waypoints:
        # 경로 전체 범위 계산
        lats = [wp['lat'] for wp in waypoints]
        lngs = [wp['lng'] for wp in waypoints]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        padding = 0.002  # 약 200m 여유

        # 음향신호기
        lights = TrafficLight.objects.filter(
            lat__range=(min_lat - padding, max_lat + padding),
            lng__range=(min_lng - padding, max_lng + padding),
            has_audio=True,
            is_operating=True
        )[:20]
        nearby['traffic_lights'] = [
            {
                'id': l.id,
                'road_nm': l.road_nm,
                'lat': l.lat,
                'lng': l.lng,
                'has_audio': l.has_audio,
                'has_remndr': l.has_remndr,
            }
            for l in lights
        ]

        # 편의시설
        facilities = Facility.objects.filter(
            lat__range=(min_lat - padding, max_lat + padding),
            lng__range=(min_lng - padding, max_lng + padding),
            is_available=True
        )[:20]
        nearby['facilities'] = [
            {
                'id': f.id,
                'name': f.name,
                'facility_type': f.facility_type,
                'lat': f.lat,
                'lng': f.lng,
                'address': f.address,
            }
            for f in facilities
        ]

        # 교통약자 이동지원센터
        centers = SupportCenter.objects.filter(
            lat__range=(min_lat - padding, max_lat + padding),
            lng__range=(min_lng - padding, max_lng + padding),
            is_operating=True
        )[:10]
        nearby['support_centers'] = [
            {
                'id': c.id,
                'name': c.name,
                'lat': c.lat,
                'lng': c.lng,
                'phone': c.phone,
            }
            for c in centers
        ]

    return Response({
        'route': route_data,
        'weather': weather,
        'weather_applied': weather_applied,
        'nearby': nearby,
    }, status=status.HTTP_201_CREATED)


# 즐겨찾기 목록 조회 / 추가
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def favorite_list(request):
    if request.method == 'GET':
        favorites = RouteFavorite.objects.filter(user=request.user)
        serializer = RouteFavoriteSerializer(favorites, many=True)
        return Response(serializer.data)

    route_id = request.data.get('route_id')
    nickname = request.data.get('nickname', '')

    try:
        route = Route.objects.get(id=route_id, user=request.user)
    except Route.DoesNotExist:
        return Response(
            {'error': '경로를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )

    favorite, created = RouteFavorite.objects.get_or_create(
        user=request.user,
        route=route,
        defaults={'nickname': nickname}
    )

    if not created:
        return Response(
            {'error': '이미 즐겨찾기에 추가된 경로입니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = RouteFavoriteSerializer(favorite)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# 즐겨찾기 삭제
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def favorite_detail(request, favorite_id):
    try:
        favorite = RouteFavorite.objects.get(id=favorite_id, user=request.user)
    except RouteFavorite.DoesNotExist:
        return Response(
            {'error': '즐겨찾기를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )
    favorite.delete()
    return Response({'message': '즐겨찾기가 삭제되었습니다.'})


# 경로 히스토리 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def route_history(request):
    history = RouteHistory.objects.filter(
        user=request.user
    ).select_related('route')[:20]
    serializer = RouteHistorySerializer(history, many=True)
    return Response(serializer.data)


# 주소 검색 (카카오 키워드 검색)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_address(request):
    query = request.query_params.get('q')
    if not query:
        return Response(
            {'error': '검색어를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    headers = {'Authorization': f'KakaoAK {API_KEY}'}
    params = {'query': query, 'size': 5}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        results = [
            {
                'name': doc['place_name'],
                'address': doc['road_address_name'] or doc['address_name'],
                'lat': float(doc['y']),
                'lng': float(doc['x']),
            }
            for doc in data.get('documents', [])
        ]
        return Response(results)
    except Exception as e:
        return Response(
            {'error': f'주소 검색 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )