from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import requests
import os

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
        is_operating=True
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
        is_operating=True
    )

    serializer = TrafficLightSerializer(lights, many=True)
    return Response(serializer.data)


# 실시간 신호 잔여시간 조회 (서울 C-ITS)
@api_view(['GET'])
@permission_classes([AllowAny])
def realtime_signal(request):
    itst_id = request.query_params.get('itst_id')

    if not itst_id:
        return Response(
            {'error': 'itst_id를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    API_KEY = os.getenv('SEOUL_API_KEY')
    BASE_URL = 'http://t-data.seoul.go.kr/apig/apiman-gateway/tapi/v2xSignalPhaseTimingInformation/1.0'

    params = {
        'apiKey': API_KEY,
        'type': 'json',
        'numOfRows': 1,
        'itstId': itst_id,
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=3)
        data = response.json()

        if not data.get('body'):
            return Response({'error': '신호 정보 없음'}, status=status.HTTP_404_NOT_FOUND)

        item = data['body'][0]

        # 보행신호 잔여시간 파싱 (센티초 → 초)
        DIRECTIONS = {
            'nt': '북쪽', 'et': '동쪽',
            'st': '남쪽', 'wt': '서쪽',
            'ne': '북동', 'se': '남동',
            'sw': '남서', 'nw': '북서',
        }

        result = {}
        for prefix, direction in DIRECTIONS.items():
            field = f"{prefix}PdsgRmdrCs"
            value = item.get(field)
            if value:
                result[direction] = round(int(value) / 10, 1)

        return Response({
            'itst_id': itst_id,
            'pedestrian_signals': result
        })

    except Exception as e:
        return Response(
            {'error': f'신호 조회 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
    
# 주변 엘리베이터 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def nearby_elevators(request):
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    radius = float(request.query_params.get('radius', 0.01))

    if not lat or not lng:
        return Response(
            {'error': '위도(lat)와 경도(lng)를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    lat, lng = float(lat), float(lng)

    elevators = Elevator.objects.filter(
        lat__range=(lat - radius, lat + radius),
        lng__range=(lng - radius, lng + radius),
        is_operating=True
    )

    serializer = ElevatorSerializer(elevators, many=True)
    return Response(serializer.data)

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

    # 복지시설은 DB에서 조회
    if place_type == 'welfare':
        radius_degree = radius / 111000  # 미터 → 도 변환 (약 111km = 1도)
        centers = SupportCenter.objects.filter(
            lat__range=(lat - radius_degree, lat + radius_degree),
            lng__range=(lng - radius_degree, lng + radius_degree),
            is_operating=True
        )[:15]
        results = [
            {
                'name': c.name,
                'address': c.address,
                'lat': c.lat,
                'lng': c.lng,
                'phone': c.phone,
                'distance': '',
                'place_url': '',
            }
            for c in centers
        ]
        return Response({
            'type': place_type,
            'count': len(results),
            'results': results,
        })

    # 병원/약국은 카카오 API로 조회
    category_map = {
        'hospital': 'HP8',
        'pharmacy': 'PM9',
        'public': 'PO3',
    }

    category_code = category_map.get(place_type, 'HP8')

    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    url = 'https://dapi.kakao.com/v2/local/search/category.json'
    headers = {'Authorization': f'KakaoAK {API_KEY}'}
    params = {
        'category_group_code': category_code,
        'x': lng,
        'y': lat,
        'radius': radius,
        'sort': 'distance',
        'size': 15,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
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
            for doc in data.get('documents', [])
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
    


    