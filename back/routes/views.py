from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import requests
import os
import math

from .models import Route, RouteFavorite, RouteHistory
from .serializers import RouteSerializer, RouteFavoriteSerializer, RouteHistorySerializer
from infrastructure.models import TrafficLight, SupportCenter
from django.utils import timezone

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
    """TMAP 응답에서 waypoints, distance, duration, crosswalks 추출"""
    waypoints = []
    crosswalks = []
    distance = 0
    duration = 0
    if not tmap_data or not tmap_data.get('features'):
        return None, 0, 0, []
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
        if geometry.get('type') == 'Point':
            turn_type = properties.get('turnType', 0)
            if turn_type in [211, 212, 213, 214, 215, 218]:
                coord = geometry['coordinates']
                crosswalks.append({
                    'lat': coord[1],
                    'lng': coord[0],
                    'description': properties.get('description', '횡단보도'),
                })
    if not waypoints:
        return None, 0, 0, []
    return waypoints, distance, duration, crosswalks


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


def calculate_safety_score(traffic_lights, danger_zones, distance, user_type):
    """안전도 점수: 횡단 횟수/장비, 이동 거리, 관리자 확인 위험구간을 반영해 1.0에서 감점.
    장거리 경로에서 감점이 무한히 누적돼 전부 0점이 되는 걸 막기 위해 항목별로 상한을 둔다."""
    crossing_penalty = 0.0
    for tl in traffic_lights or []:
        if user_type == 'disabled':
            equipped = tl.get('has_audio')
        else:
            equipped = tl.get('has_audio') or tl.get('has_remndr')
        crossing_penalty += 0.015 if equipped else 0.035
    crossing_penalty = min(crossing_penalty, 0.35)

    # 이동 거리가 길수록 외부 노출 시간이 늘어나 감점 (500m당 -0.01, 최대 -0.25)
    distance_penalty = min((distance / 500) * 0.01, 0.25) if distance else 0.0

    # 관리자가 확인한 위험구간 1건당 큰 감점 (최대 -0.45)
    danger_penalty = min(len(danger_zones or []) * 0.15, 0.45)

    score = 1.0 - crossing_penalty - distance_penalty - danger_penalty
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


def get_nearby(waypoints, crosswalks=None):
    """경로 주변 시설 정보 수집"""
    from community.models import Post

    nearby = {
        'traffic_lights': [],
        'hospitals': [],
        'pharmacies': [],
        'welfare': [],
        'danger_zones': [],
    }
    if not waypoints:
        return nearby

    # 신호등: 건너야 하는 횡단보도 위치에서 가장 가까운 DB 신호등 매칭
    seen_lights = set()
    if crosswalks:
        for cw in crosswalks:
            lat, lng = cw['lat'], cw['lng']
            MATCH_RADIUS = 0.0005  # ~50m
            lights = TrafficLight.objects.filter(
                lat__range=(lat - MATCH_RADIUS, lat + MATCH_RADIUS),
                lng__range=(lng - MATCH_RADIUS, lng + MATCH_RADIUS),
            )
            if lights.exists():
                closest = min(lights, key=lambda l: abs(l.lat - lat) + abs(l.lng - lng))
                if closest.id not in seen_lights:
                    seen_lights.add(closest.id)
                    nearby['traffic_lights'].append({
                        'id': closest.id,
                        'road_nm': closest.road_nm,
                        'description': cw.get('description', ''),
                        'lat': closest.lat,
                        'lng': closest.lng,
                        'has_audio': closest.has_audio,
                        'has_remndr': closest.has_remndr,
                    })

    # 병원/약국: 경로를 따라 300m 반경 카카오 API
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    kakao_url = 'https://dapi.kakao.com/v2/local/search/category.json'
    kakao_headers = {'Authorization': f'KakaoAK {API_KEY}'}

    total = len(waypoints)
    step = max(1, total // 5)
    check_points = waypoints[::step]
    if waypoints[-1] not in check_points:
        check_points.append(waypoints[-1])

    category_map = {
        'hospitals': 'HP8',
        'pharmacies': 'PM9',
    }

    for cat_key, cat_code in category_map.items():
        seen = set()
        for cp in check_points:
            try:
                resp = requests.get(kakao_url, headers=kakao_headers, params={
                    'category_group_code': cat_code,
                    'x': cp['lng'], 'y': cp['lat'],
                    'radius': 300, 'sort': 'distance', 'size': 5,
                }, timeout=3)
                for doc in resp.json().get('documents', []):
                    place_id = doc['id']
                    if place_id not in seen:
                        seen.add(place_id)
                        nearby[cat_key].append({
                            'name': doc['place_name'],
                            'address': doc['road_address_name'] or doc['address_name'],
                            'lat': float(doc['y']),
                            'lng': float(doc['x']),
                            'phone': doc.get('phone', ''),
                            'distance': doc.get('distance', ''),
                            'place_url': doc.get('place_url', ''),
                        })
            except Exception:
                pass

    # 복지시설: DB + 카카오 API 병행
    WELFARE_RADIUS = 0.005  # ~500m
    seen_centers = set()
    for cp in check_points:
        centers = SupportCenter.objects.filter(
            lat__range=(cp['lat'] - WELFARE_RADIUS, cp['lat'] + WELFARE_RADIUS),
            lng__range=(cp['lng'] - WELFARE_RADIUS, cp['lng'] + WELFARE_RADIUS),
            is_operating=True,
        )
        for c in centers:
            if c.id not in seen_centers:
                seen_centers.add(c.id)
                nearby['welfare'].append({
                    'id': c.id,
                    'name': c.name,
                    'address': c.address or '',
                    'lat': c.lat,
                    'lng': c.lng,
                    'phone': c.phone,
                })
    # 카카오 키워드 검색으로 복지시설/복지관 검색
    kakao_keyword_url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
    welfare_seen = set()
    for keyword in ['복지관', '복지센터', '장애인복지']:
        for cp in check_points[:2]:
            try:
                resp = requests.get(kakao_keyword_url, headers=kakao_headers, params={
                    'query': keyword,
                    'x': cp['lng'], 'y': cp['lat'],
                    'radius': 500, 'sort': 'distance', 'size': 3,
                }, timeout=3)
                for doc in resp.json().get('documents', []):
                    pid = doc['id']
                    if pid not in welfare_seen:
                        welfare_seen.add(pid)
                        nearby['welfare'].append({
                            'name': doc['place_name'],
                            'address': doc['road_address_name'] or doc['address_name'],
                            'lat': float(doc['y']),
                            'lng': float(doc['x']),
                            'phone': doc.get('phone', ''),
                            'place_url': doc.get('place_url', ''),
                        })
            except Exception:
                pass

    # 위험구간
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

    # ===== 도보 경로 4가지 탐색 =====
    if transport_type == 'walk':
        tmap1 = get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='30')
        tmap2 = get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='10')
        tmap3 = get_tmap_route(origin_lat, origin_lng, dest_lat, dest_lng, speed=user_speed, search_option='4')

        wp1, d1, dur1, cw1 = parse_tmap_route(tmap1)
        wp2, d2, dur2, cw2 = parse_tmap_route(tmap2)
        wp3, d3, dur3, cw3 = parse_tmap_route(tmap3)

        if not wp1:
            return Response({'error': '도보 경로를 찾을 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if user_speed > 0:
            dur1 = int(d1 / user_speed) if d1 else dur1
            dur2 = int(d2 / user_speed) if d2 else dur2
            dur3 = int(d3 / user_speed) if d3 else dur3

        nearby1 = get_nearby(wp1, cw1)
        nearby2 = get_nearby(wp2 or wp1, cw2 or cw1)
        nearby3 = get_nearby(wp3 or wp1, cw3 or cw1)

        safety_score = calculate_safety_score(nearby1['traffic_lights'], nearby1['danger_zones'], d1, user_type)
        safety_score2 = calculate_safety_score(nearby2['traffic_lights'], nearby2['danger_zones'], d2 or d1, user_type)
        safety_score3 = calculate_safety_score(nearby3['traffic_lights'], nearby3['danger_zones'], d3 or d1, user_type)

        if request.user.is_authenticated:
            existing = RouteHistory.objects.filter(
                user=request.user,
                route__origin_name=origin_name,
                route__dest_name=dest_name,
                route__transport_type=transport_type,
            ).first()

            if existing:
                # 기존 히스토리 날짜만 업데이트
                existing.used_at = timezone.now()
                existing.save()
            else:
                # 새 경로 + 히스토리 생성
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

        def build_route(label, wp, d, dur, score, nearby_data, cw_list):
            return {
                'label': label,
                'waypoints': wp,
                'distance': d,
                'duration': dur,
                'safety_score': score,
                'nearby': nearby_data,
                'crosswalk_count': len(cw_list) if cw_list else 0,
            }

        # 날씨추천: 비가 온다는 가정 (추천 경로 기준 20% 추가)
        dur_rain = int(dur1 * 1.2)

        return Response({
            'routes': {
                'recommend': build_route('추천', wp1, d1, dur1, safety_score, nearby1, cw1),
                'stair_free': build_route('계단회피', wp2 or wp1, d2 or d1, dur2 or dur1,
                    safety_score2, nearby2, cw2 or cw1),
                'main_road': build_route('큰길우선', wp3 or wp1, d3 or d1, dur3 or dur1,
                    safety_score3, nearby3, cw3 or cw1),
                'weather': {
                    **build_route('날씨추천', wp1, d1, dur_rain, safety_score, nearby1, cw1),
                    'weather_applied': True,
                    'message': '비가 올 경우 예상 소요시간입니다.',
                },
            },
            'weather': weather,
            'transport_type': transport_type,
        }, status=status.HTTP_201_CREATED)

    # ===== 버스/택시 경로 =====
    waypoints = []
    distance = 0
    duration = 0
    route_error = None

    transit_steps = []
    taxi_fare = None

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
                    mode = leg.get('mode', 'WALK')

                    transit_steps.append({
                        'mode': mode,
                        'route': leg.get('route', ''),
                        'route_color': leg.get('routeColor', ''),
                        'start_name': start.get('name', ''),
                        'end_name': end.get('name', ''),
                        'distance': leg.get('distance', 0),
                        'duration': leg.get('sectionTime', 0),
                    })

                    if start.get('lat') and start.get('lon'):
                        waypoints.append({'lat': start['lat'], 'lng': start['lon']})

                    # 도보 구간은 steps[].linestring, 버스/지하철 구간은 passShape.linestring 에 좌표가 들어있음
                    linestrings = [step.get('linestring', '') for step in leg.get('steps', [])]
                    if leg.get('passShape', {}).get('linestring'):
                        linestrings.append(leg['passShape']['linestring'])
                    for linestring in linestrings:
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
            summary = route_data_kakao.get('summary', {})
            distance = summary.get('distance', 0)
            duration = summary.get('duration', 0)
            taxi_fare = summary.get('fare', {})
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

    nearby = get_nearby(waypoints)
    # 택시는 차량 이동이라 보행자 신호/횡단 기준 안전도가 의미 없어 점수를 매기지 않음
    safety_score = None if transport_type == 'taxi' else calculate_safety_score(
        nearby['traffic_lights'], nearby['danger_zones'], distance, user_type
    )

    if request.user.is_authenticated:
        existing = RouteHistory.objects.filter(
            user=request.user,
            route__origin_name=origin_name,
            route__dest_name=dest_name,
            route__transport_type=transport_type,
        ).first()

        if existing:
            # 기존 히스토리 날짜만 업데이트
            existing.used_at = timezone.now()
            existing.save()
            route_data = RouteSerializer(existing.route).data
        else:
            # 새 경로 + 히스토리 생성
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
                safety_score=safety_score if safety_score is not None else 0,
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

    if transport_type == 'taxi':
        route_data['safety_score'] = None

    return Response({
        'route': route_data,
        'weather': weather,
        'weather_applied': is_bad_weather,
        'nearby': nearby,
        'transport_type': transport_type,
        'transit_steps': transit_steps,
        'taxi_fare': taxi_fare,
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
    ).select_related('route').order_by('-used_at')[:20]
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