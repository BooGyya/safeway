from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer
from django.conf import settings
from solapi import SolapiMessageService
from solapi.model import RequestMessage
import requests as req
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from config.permissions import IsAdminUser

# 회원가입
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 로그인
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    return Response(
        {'error': '아이디 또는 비밀번호가 올바르지 않습니다.'},
        status=status.HTTP_401_UNAUTHORIZED
    )


# 로그아웃
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': '로그아웃 되었습니다.'})
    except Exception:
        return Response(
            {'error': '유효하지 않은 토큰입니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )


# 프로필 조회/수정
@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    serializer = UserSerializer(
        request.user,
        data=request.data,
        partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 비밀번호 변경
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': '현재 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': '비밀번호가 변경되었습니다.'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 회원 탈퇴
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    request.user.delete()
    return Response({'message': '회원 탈퇴가 완료되었습니다.'})



# SOS 발신
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_sos(request):
    user = request.user
    
    # 보호자 번호 확인
    if not user.sos_number:
        return Response(
            {'error': '등록된 보호자 번호가 없습니다. 프로필에서 먼저 등록해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 위치 정보 받기 (프론트에서 전달)
    latitude = request.data.get('latitude', '')
    longitude = request.data.get('longitude', '')
    message_text = request.data.get('message', '')
    
    # 기본 메시지
    if not message_text:
        name = user.nickname or user.username
        message_text = f'[SafeWay SOS] {name}님이 도움을 요청합니다. 즉시 연락 바랍니다.'
    
    if latitude and longitude:
        message_text += f'\n위치: https://maps.google.com/?q={latitude},{longitude}'
    
    try:
        service = SolapiMessageService(
            api_key=settings.COOLSMS_API_KEY,
            api_secret=settings.COOLSMS_API_SECRET
        )
        
        service.send(messages=[
            RequestMessage(
                to=user.sos_number,
                from_=settings.COOLSMS_SENDER,
                text=message_text,
            )
        ])
        
        return Response({'message': 'SOS 문자가 발송되었습니다.'})
    
    except Exception as e:
        return Response(
            {'error': f'문자 발송에 실패했습니다: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
# 카카오 로그인 - 인가 코드 요청
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_login(request):
    kakao_auth_url = "https://kauth.kakao.com/oauth/authorize"
    redirect_uri = settings.KAKAO_REDIRECT_URI
    client_id = settings.KAKAO_REST_API_KEY
    
    url = f"{kakao_auth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&prompt=login"    

    return redirect(url)


# 카카오 로그인 - 콜백
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_callback(request):
    code = request.GET.get('code')
    
    if not code:
        return Response({'error': '인가 코드가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 토큰 발급
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': settings.KAKAO_REST_API_KEY,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'code': code,
    }
    token_res = req.post(token_url, data=token_data)
    token_json = token_res.json()
    access_token = token_json.get('access_token')
    
    if not access_token:
        return Response({'error': '토큰 발급 실패', 'detail': token_json}, status=status.HTTP_400_BAD_REQUEST)
        
    # 사용자 정보 조회
    user_info_url = "https://kapi.kakao.com/v2/user/me"
    user_info_res = req.get(
        user_info_url,
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_info = user_info_res.json()
    
    kakao_id = str(user_info.get('id'))
    kakao_account = user_info.get('kakao_account', {})
    email = kakao_account.get('email', f'{kakao_id}@kakao.com')
    nickname = kakao_account.get('profile', {}).get('nickname', f'kakao_{kakao_id}')
    
    # 유저 생성 또는 조회
    user, created = User.objects.get_or_create(
        username=f'kakao_{kakao_id}',
        defaults={'email': email}
    )
    
    if created:
        user.set_unusable_password()
        user.save()
    
    # JWT 토큰 발급
    refresh = RefreshToken.for_user(user)
    
    frontend_url = settings.FRONTEND_URL
    return HttpResponseRedirect(
        f"{frontend_url}/kakao/callback?"
        f"access={str(refresh.access_token)}"
        f"&refresh={str(refresh)}"
        f"&created={str(created).lower()}"
    )

# 마이페이지
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mypage(request):
    user = request.user
    
    # 최근 경로 탐색 5개
    from routes.models import RouteHistory, RouteFavorite
    recent_routes = RouteHistory.objects.filter(
        user=user
    ).select_related('route').order_by('-used_at')[:5]
    
    # 즐겨찾기 수
    favorite_count = RouteFavorite.objects.filter(user=user).count()
    
    # 내가 작성한 글
    from community.models import Post, Comment, Follow
    my_posts = Post.objects.filter(user=user).order_by('-created_at')[:5]
    my_comments = Comment.objects.filter(user=user).order_by('-created_at')[:5]
    
    # 팔로우/팔로잉 수
    following_count = Follow.objects.filter(follower=user).count()
    followers_count = Follow.objects.filter(following=user).count()
    
    return Response({
        'user': UserSerializer(user).data,
        'stats': {
            'total_routes': RouteHistory.objects.filter(user=user).count(),
            'favorite_count': favorite_count,
            'post_count': Post.objects.filter(user=user).count(),
            'following_count': following_count,
            'followers_count': followers_count,
        },
        'recent_routes': [
            {
                'id': h.route.id,
                'origin_name': h.route.origin_name,
                'dest_name': h.route.dest_name,
                'distance': h.route.distance,
                'duration': h.route.duration,
                'used_at': h.used_at,
            }
            for h in recent_routes
        ],
        'my_posts': [
            {
                'id': p.id,
                'title': p.title,
                'category': p.category,
                'reliability_score': p.reliability_score,
                'created_at': p.created_at,
            }
            for p in my_posts
        ],
        'my_comments': [
            {
                'id': c.id,
                'content': c.content,
                'post_id': c.post.id,
                'post_title': c.post.title,
                'created_at': c.created_at,
            }
            for c in my_comments
        ],
    })

# 다른 사용자 프로필 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def user_profile(request, user_id):
    from django.shortcuts import get_object_or_404
    target_user = get_object_or_404(User, id=user_id)
    
    from community.models import Post, Follow
    
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user,
            following=target_user
        ).exists()
    
    return Response({
        'id': target_user.id,
        'username': target_user.username,
        'profile_image': request.build_absolute_uri(target_user.profile_image.url) if target_user.profile_image else None,
        'user_type': target_user.user_type,
        'post_count': Post.objects.filter(user=target_user).count(),
        'following_count': Follow.objects.filter(follower=target_user).count(),
        'followers_count': Follow.objects.filter(following=target_user).count(),
        'is_following': is_following,
        'recent_posts': [
            {
                'id': p.id,
                'title': p.title,
                'category': p.category,
                'reliability_score': p.reliability_score,
                'created_at': p.created_at,
            }
            for p in Post.objects.filter(user=target_user).order_by('-created_at')[:5]
        ]
    })

# 관리자 - 사용자 목록 조회
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_user_list(request):
    from config.permissions import IsAdminUser
    users = User.objects.all().order_by('-date_joined')
    return Response([
        {
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'user_type': u.user_type,
            'is_active': u.is_active,
            'date_joined': u.date_joined,
        }
        for u in users
    ])


# 관리자 - 사용자 상태 변경 (활성/비활성)
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_user_status(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    is_active = request.data.get('is_active')

    if is_active is None:
        return Response(
            {'error': 'is_active 값을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    target_user.is_active = is_active
    target_user.save()

    return Response({
        'id': target_user.id,
        'username': target_user.username,
        'is_active': target_user.is_active,
        'message': f'사용자 상태가 {"활성화" if is_active else "비활성화"}되었습니다.'
    })