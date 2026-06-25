from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests
import os
import re
from .models import ChatHistory


def call_gms(messages, system_prompt=""):
    """GMS API 호출"""
    API_KEY = os.getenv('GMS_API_KEY')
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}',
    }
    full_messages = []
    if system_prompt:
        full_messages.append({'role': 'developer', 'content': system_prompt})
    full_messages.extend(messages)
    body = {
        'model': 'gpt-5-nano',
        'messages': full_messages,
    }
    try:
        response = requests.post(
            'https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions',
            headers=headers,
            json=body,
            timeout=30,
        )
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return None


def get_weather_info(lat, lng):
    """현재 날씨 정보 조회"""
    API_KEY = os.getenv('WEATHER_API_KEY')
    try:
        response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather',
            params={'lat': lat, 'lon': lng, 'appid': API_KEY, 'units': 'metric', 'lang': 'kr'},
            timeout=3,
        )
        data = response.json()
        return {
            'description': data['weather'][0]['description'],
            'temp': data['main']['temp'],
            'weather': data['weather'][0]['main'],
            'wind_speed': data['wind']['speed'],
        }
    except Exception:
        return None


def get_address_from_coords(lat, lng):
    """좌표를 실제 주소(행정동/도로명)로 변환"""
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    try:
        response = requests.get(
            'https://dapi.kakao.com/v2/local/geo/coord2address.json',
            headers={'Authorization': f'KakaoAK {API_KEY}'},
            params={'x': lng, 'y': lat},
            timeout=3,
        )
        docs = response.json().get('documents', [])
        if not docs:
            return None
        doc = docs[0]
        road = doc.get('road_address')
        if road and road.get('address_name'):
            return road['address_name']
        return doc.get('address', {}).get('address_name')
    except Exception:
        return None


def search_kakao_places(query, lat=None, lng=None, radius=1000, size=5):
    """카카오 키워드 장소 검색"""
    API_KEY = os.getenv('KAKAO_REST_API_KEY')
    params = {'query': query, 'size': size}
    if lat and lng:
        params.update({'x': lng, 'y': lat, 'radius': radius, 'sort': 'distance'})
    try:
        response = requests.get(
            'https://dapi.kakao.com/v2/local/search/keyword.json',
            headers={'Authorization': f'KakaoAK {API_KEY}'},
            params=params,
            timeout=3,
        )
        docs = response.json().get('documents', [])
        return [
            {
                'name': d['place_name'],
                'address': d['road_address_name'] or d['address_name'],
                'lat': float(d['y']),
                'lng': float(d['x']),
                'phone': d.get('phone', ''),
                'distance': d.get('distance', ''),
            }
            for d in docs
        ]
    except Exception:
        return []


def search_db_facilities(query, lat=None, lng=None, radius=0.01):
    """DB에서 시설 검색 (SupportCenter, Facility)"""
    from infrastructure.models import SupportCenter, Facility

    results = []

    # SupportCenter 검색
    qs = SupportCenter.objects.filter(is_operating=True)
    if lat and lng:
        qs = qs.filter(
            lat__range=(lat - radius, lat + radius),
            lng__range=(lng - radius, lng + radius),
        )
    if query:
        qs = qs.filter(name__icontains=query)
    for c in qs[:5]:
        results.append({
            'name': c.name,
            'address': c.address,
            'lat': c.lat,
            'lng': c.lng,
            'phone': c.phone,
            'type': '지원센터',
        })

    # Facility 검색 (엘리베이터, 경사로 등)
    type_map = {
        '엘리베이터': 'elevator', '경사로': 'ramp',
        '점자': 'braille', '화장실': 'toilet', '주차': 'parking',
    }
    fac_type = None
    for kw, t in type_map.items():
        if kw in query:
            fac_type = t
            break

    fqs = Facility.objects.filter(is_available=True)
    if fac_type:
        fqs = fqs.filter(facility_type=fac_type)
    if lat and lng:
        fqs = fqs.filter(
            lat__range=(lat - radius, lat + radius),
            lng__range=(lng - radius, lng + radius),
        )
    for f in fqs[:5]:
        results.append({
            'name': f.name,
            'address': f.address,
            'lat': f.lat,
            'lng': f.lng,
            'phone': '',
            'type': f.get_facility_type_display(),
        })

    return results


def detect_location_query(message):
    """위치 기반 질의 감지: '~근처', '~주변', '~에서' 패턴"""
    location_keywords = ['근처', '주변', '가까운', '인근', '에서']
    facility_keywords = [
        '복지시설', '지원센터', '병원', '약국', '엘리베이터',
        '경사로', '화장실', '주차장', '횡단보도', '신호등',
    ]
    has_location = any(kw in message for kw in location_keywords)
    has_facility = any(kw in message for kw in facility_keywords)
    return has_location and has_facility


def extract_location_from_message(message):
    """메시지에서 장소명 추출 (간단한 패턴 매칭)"""
    # '~근처', '~주변', '~에서' 앞의 장소명 추출
    patterns = [
        r'(.+?)(?:근처|주변|인근|가까운)',
        r'(.+?)(?:에서|에|의)',
    ]
    # 지시어("여기서") 또는 위치 키워드 자체("근처에")가 장소명으로 잘못 추출되는 것을 방지
    non_place_words = ['거기', '여기', '저기', '이곳', '근처', '주변', '인근', '가까운']
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            place = match.group(1).strip()
            if len(place) >= 2 and not any(d in place for d in non_place_words):
                return place
    return None


def extract_facility_keyword(message):
    """메시지에서 시설 종류 키워드만 추출 (검색 쿼리용)"""
    facility_keywords = [
        '복지시설', '지원센터', '병원', '약국', '엘리베이터',
        '경사로', '화장실', '주차장', '횡단보도', '신호등',
    ]
    for kw in facility_keywords:
        if kw in message:
            return kw
    return message


def detect_route_query(message):
    """경로 탐색 질의 감지: '~에서 ~까지', '~가는 길' 패턴"""
    route_keywords = ['가는 길', '경로', '어떻게 가', '길 알려', '길 찾아', '에서 까지', '에서']
    return any(kw in message for kw in route_keywords)


def extract_route_from_message(message):
    """메시지에서 출발지/목적지 추출"""
    # '~에서 ~까지' or '~에서 ~가는'
    patterns = [
        r'(.+?)에서\s*(.+?)(?:까지|가는|으로|로)',
        r'(.+?)(?:출발|시작).*?(.+?)(?:도착|목적지)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    return None, None


# ============================================================
# AI 챗봇 대화 (고도화)
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    message = request.data.get('message', '').strip()
    # 프론트에서 현재 위치를 전달받을 수 있음 (선택)
    user_lat = request.data.get('lat')
    user_lng = request.data.get('lng')

    if not message:
        return Response({'error': '메시지를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user

    # ── 1. 대화 맥락 유지: DB에서 최근 10개 히스토리 로드 ──
    db_history = ChatHistory.objects.filter(user=user).order_by('-created_at')[:10]
    context_messages = []
    for h in reversed(list(db_history)):
        context_messages.append({'role': 'user', 'content': h.message})
        context_messages.append({'role': 'assistant', 'content': h.response})

    # 현재 메시지 추가
    context_messages.append({'role': 'user', 'content': message})

    # ── 2. 날씨 정보 주입 ──
    weather_context = ""
    if user_lat and user_lng:
        weather = get_weather_info(float(user_lat), float(user_lng))
        if weather:
            weather_context = f"\n현재 날씨: {weather['description']}, 기온 {weather['temp']}°C, 풍속 {weather['wind_speed']}m/s"
            bad = ['Rain', 'Snow', 'Thunderstorm', 'Drizzle']
            if weather['weather'] in bad or weather['wind_speed'] > 10:
                weather_context += "\n⚠️ 현재 날씨가 좋지 않습니다. 이동 시 주의를 권고해주세요."

    # ── 3. 경로 탐색 질의 감지 ──
    route_action = None
    if detect_route_query(message):
        origin, dest = extract_route_from_message(message)
        if origin and dest:
            route_action = {'type': 'route', 'origin': origin, 'dest': dest}

    # ── 4. 위치 기반 시설 질의 처리 ──
    facility_context = ""
    if detect_location_query(message):
        place_name = extract_location_from_message(message)
        search_lat, search_lng = user_lat, user_lng

        # 장소명이 있으면 카카오로 좌표 조회
        if place_name:
            places = search_kakao_places(place_name)
            if places:
                search_lat = places[0]['lat']
                search_lng = places[0]['lng']

        if search_lat and search_lng:
            facility_query = extract_facility_keyword(message)
            # DB 시설 검색
            db_results = search_db_facilities(facility_query, float(search_lat), float(search_lng))
            # 카카오 장소 검색 (복지시설, 병원, 약국 등). 좁은 반경에 결과가 없으면 반경을 넓혀 재시도
            kakao_results = []
            for radius in (1000, 3000, 5000):
                kakao_results = search_kakao_places(facility_query, float(search_lat), float(search_lng), radius=radius)
                if kakao_results:
                    break

            all_results = db_results + kakao_results
            if all_results:
                facility_context = f"\n\n[검색된 주변 시설 {len(all_results)}곳]\n"
                for i, f in enumerate(all_results[:7], 1):
                    facility_context += f"{i}. {f['name']}"
                    if f.get('address'):
                        facility_context += f" - {f['address']}"
                    if f.get('phone'):
                        facility_context += f" (☎ {f['phone']})"
                    if f.get('distance'):
                        facility_context += f" [{f['distance']}m]"
                    facility_context += "\n"

    # ── 5. 시스템 프롬프트 구성 ──
    if user_lat and user_lng:
        current_address = get_address_from_coords(float(user_lat), float(user_lng))
        location_status = (
            f"현재 사용자의 위치는 '{current_address}' 입니다." if current_address
            else "현재 사용자의 위치 정보가 이미 확인되어 있습니다."
        )
        location_status += (
            " 위치 공유 여부나 검색 반경을 다시 묻지 말고 바로 주변 시설을 안내해주세요. "
            "사용자가 현재 위치(주소)를 물으면 위 주소를 그대로 알려주세요."
        )
    else:
        location_status = "현재 사용자의 위치 정보가 없습니다. 위치 공유를 요청하거나 구체적인 장소명을 물어봐주세요."
    no_result_guide = (
        "\n\n검색을 시도했지만 주변에서 결과를 찾지 못했습니다. 위치를 다시 묻지 말고, "
        "주변에 해당 시설이 없다는 점을 사용자에게 명확히 알려주세요."
        if (detect_location_query(message) and user_lat and user_lng and not facility_context)
        else ""
    )
    route_guide = (
        "\n\n출발지와 목적지가 감지되어 지도 화면에서 실제 도보 경로를 계산해 보여줄 예정입니다. "
        "지하철 호선, 환승, 출구, 정류장, 소요시간 등 실시간 대중교통 정보는 추측해서 말하지 마세요. "
        "지도에서 경로를 확인할 수 있다고 안내하고, 필요하면 날씨나 보행 속도에 따른 일반적인 이동 조언만 덧붙이세요."
        if route_action else ""
    )

    system_prompt = f"""당신은 SafeWay의 AI 안내 도우미입니다.
교통약자(장애인, 노인, 휠체어 사용자, 임산부 등)의 안전한 이동을 돕는 서비스입니다.

현재 사용자 정보:
- 사용자 유형: {user.user_type}
- 보행 속도: {user.walk_speed} m/s{weather_context}
- 위치 상태: {location_status}

역할:
1. 경로 안내 및 주변 시설 안내
2. 신호등/음향신호기/경사로/엘리베이터 관련 질문 답변
3. 날씨에 따른 이동 조언
4. 교통약자 관련 정보 제공

{facility_context}{no_result_guide}{route_guide}

위 시설 정보가 있다면 이를 바탕으로 구체적으로 안내해주세요. 사용자의 위치 정보가 이미 확인된 상태라면
위치 공유나 검색 반경에 대해 다시 묻지 마세요.
항상 친절하고 명확하게 한국어로 답변해주세요."""

    # ── 6. LLM 호출 ──
    response_text = call_gms(context_messages, system_prompt)

    if not response_text:
        return Response({'error': 'AI 응답을 받지 못했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── 7. 히스토리 저장 ──
    ChatHistory.objects.create(user=user, message=message, response=response_text)

    response_data = {
        'message': response_text,
        'role': 'assistant',
    }

    # 경로 탐색 액션이 감지된 경우 프론트에 전달
    if route_action:
        response_data['action'] = route_action

    return Response(response_data)


# ============================================================
# LLM 부적절 표현 필터링
# ============================================================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_content(request):
    content = request.data.get('content')
    if not content:
        return Response({'error': '검사할 내용을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    system_prompt = "당신은 콘텐츠 필터링 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
    messages = [{'role': 'user', 'content': f"""다음 텍스트에 욕설, 혐오, 비방, 선정적 표현이 포함되어 있는지 확인해주세요.

텍스트: {content}

반드시 아래 JSON 형식으로만 응답하세요.
{{"is_inappropriate": true/false, "reason": "이유"}}"""}]

    response_text = call_gms(messages, system_prompt)
    if not response_text:
        return Response({'is_inappropriate': False, 'reason': '필터링 실패'})

    try:
        import json
        clean = response_text.strip()
        if '```' in clean:
            clean = clean.split('```')[1]
            if clean.startswith('json'):
                clean = clean[4:]
        result = json.loads(clean.strip())
        return Response(result)
    except Exception:
        return Response({'is_inappropriate': False, 'reason': '파싱 실패'})


# ============================================================
# 관리자 기능
# ============================================================
from config.permissions import IsAdminUser


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_filter_monitor(request):
    """게시글 목록 일괄 필터링"""
    from community.models import Post
    import json

    posts = Post.objects.filter(is_trusted=False).order_by('-created_at')[:50]
    results = []
    for post in posts:
        content = f"제목: {post.title}\n내용: {post.content}"
        system_prompt = "당신은 콘텐츠 필터링 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
        messages = [{'role': 'user', 'content': f"""다음 텍스트에 욕설, 혐오, 비방, 선정적 표현이 포함되어 있는지 확인해주세요.

텍스트: {content}

반드시 아래 JSON 형식으로만 응답하세요.
{{"is_inappropriate": true/false, "reason": "이유"}}"""}]

        response_text = call_gms(messages, system_prompt)
        try:
            clean = response_text.strip()
            if '```' in clean:
                clean = clean.split('```')[1]
                if clean.startswith('json'):
                    clean = clean[4:]
            result = json.loads(clean.strip())
            results.append({
                'post_id': post.id,
                'title': post.title,
                'is_inappropriate': result.get('is_inappropriate', False),
                'reason': result.get('reason', ''),
            })
        except Exception:
            results.append({
                'post_id': post.id,
                'title': post.title,
                'is_inappropriate': False,
                'reason': '파싱 실패',
            })

    return Response(results)


# ============================================================
# 챗봇 히스토리 조회 / 삭제
# ============================================================
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def chat_history(request):
    if request.method == 'GET':
        history = ChatHistory.objects.filter(user=request.user)[:20]
        return Response([
            {
                'id': h.id,
                'message': h.message,
                'response': h.response,
                'created_at': h.created_at,
            }
            for h in history
        ])
    # DELETE: 전체 히스토리 삭제
    ChatHistory.objects.filter(user=request.user).delete()
    return Response({'message': '대화 기록이 삭제되었습니다.'})