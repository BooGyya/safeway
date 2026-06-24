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
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=1.0, search_option='0'):
    """TMAP 보행자 경로 탐색"""
    API_KEY = os.getenv('TMAP_API_KEY')
    url = 'https://apis.openapi.sk.com/tmap/routes/pedestrian'
    headers = {
        'appKey': API_KEY,
        'Content-Type': 'application/json',
    }
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
        'searchOption': search_option,
    }
    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        return response.json()
    except Exception as e:
        print(f"TMAP 경로 탐색 오류: {e}")
        return None


def parse_tmap_route(tmap_data):
    """TMAP 응답에서 waypoints, distance, duration 추출"""
    waypoints = []
    distance = 0
    duration = 0
    if not tmap_data or not tmap_data.get('features'):
        return None, 0, 0
    for feature in tmap_data['features']:
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        if properties.get('totalDistance'):
            distance = properties['totalDistance']
        if properties.get('totalTime'):
            duration = properties['totalTime']
        if geometry.get('type') == 'LineString':
            for coord in geometry.get('coordinates', []):
                waypoints.append({'lat': coord[1], 'lng': coord[0]})
    if not waypoints:
        return None, 0, 0
    return waypoints, distance, duration


def get_tmap_transit_route(origin_lat, origin_lng, dest_lat, dest_lng):
    """TMAP 대중교통 경로 탐색"""
    API_KEY = os.getenv('TMAP_API_KEY')
    url = 'https://apis.openapi.sk.com/transit/routes'
    headers = {
        'appKey': API_KEY,
        'Content-Type': 'application/json',
    }
    body = {
        'startX': str(origin_lng),
        'startY': str(origin_lat),
        'endX': str(dest_lng),
        'endY': str(dest_lat),
        'reqCoordType': 'WGS84GEO',
        'resCoordType': 'WGS84GEO',
        'count': 1,
    }
    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        return response.json()
    except Exception as e:
        print(f"TMAP 대중교통 경로 탐색 오류: {e}")
        return None


def get_kakao_car_route(origin_lat, origin_lng, dest_lat, dest_lng):
    """카카오 자동차 경로 탐색 (택시용)"""
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    url = 'https://apis-navi.kakaomobility.com/v1/directions'
    headers = {'Authorization': f'KakaoAK {API_KEY}'}
    params = {
        'origin': f'{origin_lng},{origin_lat}',
        'destination': f'{dest_lng},{dest_lat}',
        'priority': 'RECOMMEND',
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        return response.json()
    except Exception as e:
        print(f"카카오 자동차 경로 탐색 오류: {e}")
        return None


def calculate_safety_score(waypoints, user_type):
    if not waypoints:
        return 0.5
    lats = [wp['lat'] for wp in waypoints]
    lngs = [wp['lng'] for wp in waypoints]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    padding = 0.001
    lights = TrafficLight.objects.filter(
        lat__range=(min_lat - padding, max_lat + padding),
        lng__range=(min_lng - padding, max_lng + padding),
    )
    total = lights.count()
    if total == 0:
        return 0.5
    audio_count = lights.filter(has_audio=True).count()
    remndr_count = lights.filter(has_remndr=True).count()
    if user_type == 'disabled':
        score = (audio_count / total) * 0.7 + (remndr_count / total) * 0.3
    else:
        score = (audio_count / total) * 0.4 + (remndr_count / total) * 0.6
    return round(max(0.0, min(1.0, score)), 2)


def get_weather_info(lat, lng):
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


def get_nearby(waypoints):
    """경로 주변 편의시설 정보 수집"""
    from community.models import Post

    nearby = {
        'traffic_lights': [],
        'facilities': [],
        'support_centers': [],
        'danger_zones': [],
    }
    if not waypoints:
        return nearby

    total = len(waypoints)
    step = max(1, total // 15)
    sampled = waypoints[::step]
    RADIUS = 0.003
    seen_lights = set()
    seen_facilities = set()
    seen_centers = set()

    for wp in sampled:
        lat, lng = wp['lat'], wp['lng']
        if len(nearby['traffic_lights']) < 20:
            lights = TrafficLight.objects.filter(
                lat__range=(lat - RADIUS, lat + RADIUS),
                lng__range=(lng - RADIUS, lng + RADIUS),
            )
            for l in lights:
                if l.id not in seen_lights:
                    seen_lights.add(l.id)
                    nearby['traffic_lights'].append({
                        'id': l.id,
                        'road_nm': l.road_nm,
                        'lat': l.lat,
                        'lng': l.lng,
                        'has_audio': l.has_audio,
                        'has_remndr': l.has_remndr,
                    })
        if len(nearby['facilities']) < 100:
            facilities = Facility.objects.filter(
                lat__range=(lat - RADIUS, lat + RADIUS),
                lng__range=(lng - RADIUS, lng + RADIUS),
                is_available=True,
            )
            for f in facilities:
                if f.id not in seen_facilities:
                    seen_facilities.add(f.id)
                    nearby['facilities'].append({
                        'id': f.id,
                        'name': f.name,
                        'facility_type': f.facility_type,
                        'lat': f.lat,
                        'lng': f.lng,
                        'address': f.address,
                    })
        if len(nearby['support_centers']) < 10:
            centers = SupportCenter.objects.filter(
                lat__range=(lat - RADIUS, lat + RADIUS),
                lng__range=(lng - RADIUS, lng + RADIUS),
                is_operating=True,
            )
            for c in centers:
                if c.id not in seen_centers:
                    seen_centers.add(c.id)
                    nearby['support_centers'].append({
                        'id': c.id,
                        'name': c.name,
                        'lat': c.lat,
                        'lng': c.lng,
                        'phone': c.phone,
                    })

    nearby['traffic_lights'] = nearby['traffic_lights'][:20]
    nearby['facilities'] = nearby['facilities'][:20]
    nearby['support_centers'] = nearby['support_centers'][:10]

    lats = [wp['lat'] for wp in waypoints]
    lngs = [wp['lng'] for wp in waypoints]
    danger_posts = Post.objects.filter(
        is_trusted=True,
        latitude__isnull=False,
        longitude__isnull=False,
        category__in=['danger', 'obstacle', 'broken', 'construction'],
        latitude__range=(min(lats) - 0.005, max(lats) + 0.005),
        longitude__range=(min(lngs) - 0.005, max(lngs) + 0.005),
    )
    for dp in danger_posts[:15]:
        nearby['danger_zones'].append({
            'id': dp.id,
            'title': dp.title,
            'category': dp.category,
            'category_label': dict(Post.CATEGORY_CHOICES).get(dp.category, dp.category),
            'lat': float(dp.latitude),
            'lng': float(dp.longitude),
            'address': dp.address,
        })

    return nearby


# 경로 탐색
@api_view(['POST'])
@permission_classes([AllowAny])
def search_route(request):
    transport_type = request.data.get('transport_type', 'walk')
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

    user_speed = float(request.data.get('walk_speed',
        request.user.walk_speed if request.user.is_authenticated else 1.0))
    user_type = request.data.get('user_type',
        request.user.user_type if request.user.is_authenticated else 'normal')

    # 날씨 정보 먼저 조회
    weather = get_weather_info(origin_lat, origin_lng)
    bad_weather = ['Rain', 'Snow', 'Thunderstorm', 'Drizzle']
    is_bad_weather = weather and (
        weather['weather'] in bad_weather or weather['wind_speed'] > 10
    )

    # 날씨 메시지
    weather_messages = {
        'Rain': '비가 오고 있어요. 우산을 챙기세요.',
        'Snow': '눈이 오고 있어요. 미끄럼 주의하세요.',
        'Thunderstorm': '천둥번개가 치고 있어요. 실내 이동을 권장해요.',
        'Drizzle': '이슬비가 내리고 있어요. 우산을 챙기세요.',
    }

    # ===== 도보 경로 4가지 탐색 =====
    if transport_type == 'walk':
        # 1. 추천 경로
        wp1, d1, dur1 = parse_tmap_route(
            get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='0')
        )
        # 2. 계단회피 경로
        wp2, d2, dur2 = parse_tmap_route(
            get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='10')
        )
        # 3. 큰길우선 경로
        wp3, d3, dur3 = parse_tmap_route(
            get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='4')
        )

        if not wp1:
            return Response({'error': '도보 경로를 찾을 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # 보행속도로 duration 재계산
        if user_speed > 0:
            dur1 = int(d1 / user_speed) if d1 else dur1
            dur2 = int(d2 / user_speed) if d2 else dur2
            dur3 = int(d3 / user_speed) if d3 else dur3

        # 4. 날씨 추천 경로 (악천후면 소요시간 20% 추가)
        weather_msg = None
        if is_bad_weather:
            weather_msg = weather_messages.get(weather['weather'], '날씨가 좋지 않아요. 이동 시 주의하세요.')
            dur_weather = int(dur1 * 1.2)
        else:
            dur_weather = dur1

        # 추천 경로 기준으로 DB 저장
        safety_score = calculate_safety_score(wp1, user_type)
        nearby = get_nearby(wp1)

        if request.user.is_authenticated:
            route = Route.objects.create(
                user=request.user,
                origin_name=origin_name,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                dest_name=dest_name,
                dest_lat=dest_lat,
                dest_lng=dest_lng,
                distance=d1,
                duration=dur1,
                safety_score=safety_score,
                waypoints=wp1,
                weather_applied=is_bad_weather,
                transport_type=transport_type,
            )
            RouteHistory.objects.create(user=request.user, route=route)

        return Response({
            'routes': {
                'recommend': {
                    'label': '추천',
                    'waypoints': wp1,
                    'distance': d1,
                    'duration': dur1,
                    'safety_score': safety_score,
                },
                'stair_free': {
                    'label': '계단회피',
                    'waypoints': wp2 or wp1,
                    'distance': d2 or d1,
                    'duration': dur2 or dur1,
                    'safety_score': calculate_safety_score(wp2 or wp1, user_type),
                },
                'main_road': {
                    'label': '큰길우선',
                    'waypoints': wp3 or wp1,
                    'distance': d3 or d1,
                    'duration': dur3 or dur1,
                    'safety_score': calculate_safety_score(wp3 or wp1, user_type),
                },
                'weather': {
                    'label': '날씨추천',
                    'waypoints': wp1,
                    'distance': d1,
                    'duration': dur_weather,
                    'safety_score': safety_score,
                    'weather_applied': is_bad_weather,
                    'message': weather_msg,
                },
            },
            'weather': weather,
            'nearby': nearby,
            'transport_type': transport_type,
        }, status=status.HTTP_201_CREATED)

    # ===== 버스/택시 경로 =====
    waypoints = []
    distance = 0
    duration = 0
    route_error = None

    if transport_type == 'bus':
        tmap_data = get_tmap_transit_route(origin_lat, origin_lng, dest_lat, dest_lng)
        if not tmap_data or not tmap_data.get('metaData'):
            route_error = '대중교통 경로를 찾을 수 없습니다.'
        else:
            plan = tmap_data['metaData'].get('plan', {})
            itineraries = plan.get('itineraries', [])
            if itineraries:
                best = itineraries[0]
                distance = best.get('totalDistance', 0)
                duration = best.get('totalTime', 0)
                for leg in best.get('legs', []):
                    start = leg.get('start', {})
                    end = leg.get('end', {})
                    if start.get('lat') and start.get('lon'):
                        waypoints.append({'lat': start['lat'], 'lng': start['lon']})
                    for step in leg.get('steps', []):
                        linestring = step.get('linestring', '')
                        if linestring:
                            for coord in linestring.split(' '):
                                parts = coord.split(',')
                                if len(parts) == 2:
                                    try:
                                        waypoints.append({
                                            'lat': float(parts[1]),
                                            'lng': float(parts[0]),
                                        })
                                    except ValueError:
                                        pass
                    if end.get('lat') and end.get('lon'):
                        waypoints.append({'lat': end['lat'], 'lng': end['lon']})
            else:
                route_error = '대중교통 경로를 찾을 수 없습니다.'

    elif transport_type == 'taxi':
        tmap_data = get_kakao_car_route(origin_lat, origin_lng, dest_lat, dest_lng)
        if not tmap_data or not tmap_data.get('routes'):
            route_error = '택시 경로를 찾을 수 없습니다.'
        else:
            route_data_kakao = tmap_data['routes'][0]
            distance = route_data_kakao.get('summary', {}).get('distance', 0)
            duration = route_data_kakao.get('summary', {}).get('duration', 0)
            for section in route_data_kakao.get('sections', []):
                for road in section.get('roads', []):
                    vertexes = road.get('vertexes', [])
                    for i in range(0, len(vertexes) - 1, 2):
                        waypoints.append({
                            'lat': vertexes[i+1],
                            'lng': vertexes[i],
                        })

    if route_error:
        return Response({'error': route_error}, status=status.HTTP_400_BAD_REQUEST)

    if is_bad_weather:
        duration = int(duration * 1.2)

    safety_score = calculate_safety_score(waypoints, user_type)
    nearby = get_nearby(waypoints)

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
            weather_applied=is_bad_weather,
            transport_type=transport_type,
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
            'weather_applied': is_bad_weather,
        }

    return Response({
        'route': route_data,
        'weather': weather,
        'weather_applied': is_bad_weather,
        'nearby': nearby,
        'transport_type': transport_type,
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


# 즐겨찾기 수정 / 삭제
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def favorite_detail(request, favorite_id):
    try:
        favorite = RouteFavorite.objects.get(id=favorite_id, user=request.user)
    except RouteFavorite.DoesNotExist:
        return Response(
            {'error': '즐겨찾기를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'PATCH':
        nickname = request.data.get('nickname')
        if nickname:
            favorite.nickname = nickname
            favorite.save()
        serializer = RouteFavoriteSerializer(favorite)
        return Response(serializer.data)

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