from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import requests
import os
from .models import ChatHistory


def call_gms(messages, system_prompt=""):
    """GMS API 호출"""
    API_KEY = os.getenv('GMS_API_KEY')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}',
    }

    # system 메시지 맨 앞에 추가
    full_messages = []
    if system_prompt:
        full_messages.append({
            'role': 'developer',
            'content': system_prompt,
        })
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


# AI 챗봇 대화
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    message = request.data.get('message')
    history = request.data.get('history', [])

    if not message:
        return Response(
            {'error': '메시지를 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user
    system_prompt = f"""
    당신은 SafeWay의 AI 안내 도우미예요.
    교통약자(장애인, 노인, 휠체어 사용자, 임산부 등)의 안전한 이동을 돕는 서비스입니다.

    현재 사용자 정보:
    - 사용자 유형: {user.user_type}
    - 보행 속도: {user.walk_speed} m/s

    다음 역할을 수행해주세요.
    1. 경로 안내 및 주변 시설 안내
    2. 신호등/음향신호기/경사로/엘리베이터 관련 질문 답변
    3. 날씨에 따른 이동 조언
    4. 교통약자 관련 정보 제공

    항상 친절하고 명확하게 한국어로 답변해주세요.
    """

    # 대화 히스토리 구성
    messages = []
    for h in history:
        messages.append({
            'role': h.get('role'),
            'content': h.get('content'),
        })
    messages.append({'role': 'user', 'content': message})

    response_text = call_gms(messages, system_prompt)

    if not response_text:
        return Response(
            {'error': 'AI 응답을 받지 못했습니다.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 대화 히스토리 저장
    ChatHistory.objects.create(
        user=user,
        message=message,
        response=response_text,
    )

    return Response({
        'message': response_text,
        'role': 'assistant',
    })

# LLM 부적절 표현 필터링
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filter_content(request):
    content = request.data.get('content')

    if not content:
        return Response(
            {'error': '검사할 내용을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    system_prompt = "당신은 콘텐츠 필터링 전문가입니다. 반드시 JSON 형식으로만 응답하세요."

    messages = [{
        'role': 'user',
        'content': f"""다음 텍스트에 욕설, 혐오, 비방, 선정적 표현이 포함되어 있는지 확인해주세요.

텍스트: {content}

반드시 아래 JSON 형식으로만 응답하세요.
{{"is_inappropriate": true/false, "reason": "이유"}}"""
    }]

    response_text = call_gms(messages, system_prompt)

    if not response_text:
        return Response({'is_inappropriate': False, 'reason': '필터링 실패'})

    try:
        import json
        # JSON 파싱
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


# 관리자 - LLM 필터링 모니터링
@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_filter_monitor(request):
    """게시글 목록 일괄 필터링"""
    from community.models import Post

    posts = Post.objects.filter(is_trusted=False).order_by('-created_at')[:50]

    results = []
    for post in posts:
        content = f"제목: {post.title}\n내용: {post.content}"
        system_prompt = "당신은 콘텐츠 필터링 전문가입니다. 반드시 JSON 형식으로만 응답하세요."
        messages = [{
            'role': 'user',
            'content': f"""다음 텍스트에 욕설, 혐오, 비방, 선정적 표현이 포함되어 있는지 확인해주세요.

텍스트: {content}

반드시 아래 JSON 형식으로만 응답하세요.
{{"is_inappropriate": true/false, "reason": "이유"}}"""
        }]

        response_text = call_gms(messages, system_prompt)

        try:
            import json
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

# 챗봇 히스토리 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_history(request):
    from .models import ChatHistory
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