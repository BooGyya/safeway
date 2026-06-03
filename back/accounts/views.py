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
        message_text = f'[SafeWay SOS] {user.username}님이 도움을 요청합니다.'
    
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