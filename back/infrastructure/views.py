from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
import os
from django.shortcuts import get_object_or_404
from .models import TrafficLight, Facility, Elevator, SupportCenter
from .serializers import (
    TrafficLightSerializer, FacilitySerializer,
    ElevatorSerializer, SupportCenterSerializer
)


# 주변 신호등 조회 (위경도 기반)
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_traffic_lights(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 0.01))  # 약 1km

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    lights = TrafficLight.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
    )

    serializer = TrafficLightSerializer(lights, many=True)
    return Response(serializer.data)


# 음향신호기 있는 신호등만 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def audio_traffic_lights(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 0.01))

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    lights = TrafficLight.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
        has_audio=True,
    )

    serializer = TrafficLightSerializer(lights, many=True)
    return Response(serializer.data)


def fetch_realtime_pedestrian_signal(itst_id):
    """itstId로 V2X 실시간 보행신호 잔여시간(초) 조회. 방향별 dict 또는 None."""
    API_KEY = os.getenv('SEOUL_TDATA_API_KEY')
    BASE_URL = 'http://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0'
    DIRECTIONS = {
        'nt': '북쪽', 'et': '동쪽',
        'st': '남쪽', 'wt': '서쪽',
        'ne': '북동', 'se': '남동',
        'sw': '남서', 'nw': '북서',
    }
    try:
        response = requests.get(
            BASE_URL,
            params={'apikey': API_KEY, 'type': 'json', 'numOfRows': 1, 'itstId': itst_id},
            timeout=5,
        )
        data = response.json()
        if not data:
            return None
        item = data[0]

        UNKNOWN_VALUE = 36001  # 해당 방향이 보행 녹색이 아닐 때 들어오는 "값 없음" 센티넬

        result = {}
        for prefix, direction in DIRECTIONS.items():
            value = item.get(f"{prefix}PdsgRmdrCs")
            if value and value < UNKNOWN_VALUE:
                # 데시초(1/10초) 단위
                result[direction] = round(float(value) / 10, 1)
        return result or None
    except Exception:
        return None


# 실시간 신호 잔여시간 조회 (서울 V2X)
@api_view(['GET'])
@permission_classes([AllowAny])
def realtime_signal(request):
    itst_id = request.query_params.get('itst_id')

    if not itst_id:
        return Response(
            {'error': 'itst_id를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = fetch_realtime_pedestrian_signal(itst_id)
    if result is None:
        return Response({'error': '신호 정보 없음'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'itst_id': itst_id,
        'pedestrian_signals': result
    })


# 주변 장애인 편의시설 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_facilities(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 0.01))
    facility_type = request.query_params.get('type')

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    facilities = Facility.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
        is_available=True
    )

    if facility_type:
        facilities = facilities.filter(facility_type=facility_type)

    serializer = FacilitySerializer(facilities, many=True)
    return Response(serializer.data)


# 주변 교통약자 이동지원센터 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_support_centers(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 0.05))

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    centers = SupportCenter.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
        is_operating=True
    )

    serializer = SupportCenterSerializer(centers, many=True)
    return Response(serializer.data)


# 서울 실시간 혼잡도 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def seoul_congestion(request):
    area_nm = request.query_params.get('area_nm')

    if not area_nm:
        return Response(
            {'error': 'area_nm을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    API_KEY = os.getenv('SEOUL_API_KEY')
    url = f'http://openapi.seoul.go.kr:8088/{API_KEY}/json/citydata_ppltn/1/1/{area_nm}'

    try:
        response = requests.get(url, timeout=3)
        data = response.json()
        ppltn_data = data.get('SeoulRtd.citydata_ppltn', [{}])[0]

        return Response({
            'area_nm': area_nm,
            'congestion_lvl': ppltn_data.get('AREA_CONGEST_LVL', ''),
            'congestion_msg': ppltn_data.get('AREA_CONGEST_MSG', ''),
        })

    except Exception as e:
        return Response(
            {'error': f'혼잡도 조회 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
# 주변 지하철역 엘리베이터 조회 (DB 기반, 현재 서울/대전만 데이터 보유)
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_elevators(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius_m = float(request.query_params.get('radius', 2000))
    radius = radius_m / 111000  # 미터를 위경도 도(degree) 단위로 환산

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    elevators = Elevator.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
        is_operating=True,
    )

    def format_elevator(e):
        if e.sido == '서울':
            # sigungu: 구 이름, install_place: 읍면동명
            return {
                'id': e.id,
                'name': f'{e.building_nm}역',
                'address': f'서울 {e.sigungu} {e.install_place}',
                'lat': e.lat,
                'lng': e.lng,
                'description': '지하철역 엘리베이터',
            }
        # 대전: sigungu에 호기 번호, install_place에 설치 위치(출구), elevator_type에 내/외부
        return {
            'id': e.id,
            'name': f'{e.building_nm} {e.sigungu}호기'.strip(),
            'address': e.address,
            'lat': e.lat,
            'lng': e.lng,
            'description': f'{e.install_place} ({e.elevator_type}부)' if e.install_place else e.elevator_type,
        }

    results = [format_elevator(e) for e in elevators]
    return Response({
        'count': len(results),
        'results': results,
    })

# 주변 병원/복지시설/약국 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_places(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    place_type = request.query_params.get('type', 'hospital')
    radius = int(request.query_params.get('radius', 1000))

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    headers = {'Authorization': f'KakaoAK {API_KEY}'}

    try:
        if place_type == 'welfare':
            search_keywords = ['사회복지', '복지관', '복지센터']
            all_docs = []
            seen_ids = set()

            for keyword in search_keywords:
                url = 'https://dapi.kakao.com/v2/local/search/keyword.json'
                params = {
                    'query': keyword,
                    'x': lng,
                    'y': lat,
                    'radius': radius,
                    'sort': 'distance',
                    'size': 15,
                }
                resp = requests.get(url, headers=headers, params=params, timeout=5)
                for doc in resp.json().get('documents', []):
                    if doc['id'] not in seen_ids:
                        seen_ids.add(doc['id'])
                        all_docs.append(doc)

            EXCLUDE_KEYWORDS = ['대학교', '대학원', '유치원', '학교', '학원', '식당', '카페', '마트', '키즈']
            docs = [
                doc for doc in all_docs
                if not any(kw in doc['place_name'] for kw in EXCLUDE_KEYWORDS)
            ]
            docs = sorted(docs, key=lambda x: int(x.get('distance', 0)))[:30]

        else:
            category_map = {
                'hospital': 'HP8',
                'pharmacy': 'PM9',
                'public': 'PO3',
            }
            category_code = category_map.get(place_type, 'HP8')
            url = 'https://dapi.kakao.com/v2/local/search/category.json'
            params = {
                'category_group_code': category_code,
                'x': lng,
                'y': lat,
                'radius': radius,
                'sort': 'distance',
                'size': 15,
            }
            resp = requests.get(url, headers=headers, params=params, timeout=5)
            docs = resp.json().get('documents', [])

        results = [
            {
                'name': doc['place_name'],
                'address': doc['road_address_name'] or doc['address_name'],
                'lat': float(doc['y']),
                'lng': float(doc['x']),
                'phone': doc.get('phone', ''),
                'distance': doc.get('distance', ''),
                'place_url': doc.get('place_url', ''),
            }
            for doc in docs
        ]
        return Response({
            'type': place_type,
            'count': len(results),
            'results': results,
        })
    except Exception as e:
        return Response(
            {'error': f'장소 검색 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    


# 시설 검색 (시설명 검색)
@api_view(['GET'])
@permission_classes([AllowAny])
def search_facilities(request):
    keyword = request.query_params.get('q', '')
    facility_type = request.query_params.get('type', '')

    if not keyword:
        return Response(
            {'error': '검색어를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    facilities = Facility.objects.filter(
        name__icontains=keyword,
        is_available=True
    )

    if facility_type:
        facilities = facilities.filter(facility_type=facility_type)

    facilities = facilities[:20]

    serializer = FacilitySerializer(facilities, many=True)
    return Response(serializer.data)

# 시설 상세 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def facility_detail(request, facility_id):
    facility = get_object_or_404(Facility, id=facility_id)
    serializer = FacilitySerializer(facility)
    return Response(serializer.data)