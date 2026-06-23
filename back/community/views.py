from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import Post, Comment, PostLike, Follow, PostImage
from .serializers import (
    PostSerializer, PostDetailSerializer,
    CommentSerializer, FollowSerializer
)
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


# 게시글 목록 조회 / 생성
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_list(request):
    if request.method == 'GET':
        sort = request.query_params.get('sort', 'latest')
        keyword = request.query_params.get('q', '')
        category = request.query_params.get('category', '')

        posts = Post.objects.all()

        if keyword:
            posts = posts.filter(
                models.Q(title__icontains=keyword) |
                models.Q(content__icontains=keyword)
            )

        if category:
            posts = posts.filter(category=category)

        if sort == 'reliability':
            posts = posts.order_by('-reliability_score', '-created_at')
        elif sort == 'following' and request.user.is_authenticated:
            following_users = request.user.following.values_list(
                'following_id', flat=True
            )
            posts = posts.order_by(
                '-is_trusted', '-created_at'
            ).filter(user_id__in=following_users) | posts.exclude(
                user_id__in=following_users
            ).order_by('-created_at')
        else:
            posts = posts.order_by('-created_at')

        # 페이지네이션
        paginator = PageNumberPagination()
        paginator.page_size = 10
        result_page = paginator.paginate_queryset(posts, request)
        serializer = PostSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    # 게시글 생성
    serializer = PostSerializer(data=request.data)
    if serializer.is_valid():
        # LLM 필터링
        from chatbot.views import call_gms
        import json

        title = request.data.get('title', '')
        content = request.data.get('content', '')

        filter_messages = [{
            'role': 'user',
            'content': f"""다음 텍스트에 욕설, 혐오, 비방, 선정적 표현이 포함되어 있는지 확인해주세요.

        텍스트: 제목: {title}\n내용: {content}

        반드시 아래 JSON 형식으로만 응답하세요.
        {{"is_inappropriate": true/false, "reason": "이유"}}"""
        }]

        filter_result = call_gms(filter_messages, "당신은 콘텐츠 필터링 전문가입니다. 반드시 JSON 형식으로만 응답하세요.")

        try:
            clean = filter_result.strip()
            if '```' in clean:
                clean = clean.split('```')[1]
                if clean.startswith('json'):
                    clean = clean[4:]
            result = json.loads(clean.strip())

            if result.get('is_inappropriate'):
                return Response(
                    {'error': f'부적절한 내용이 포함되어 있습니다: {result.get("reason")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            pass  # 필터링 실패 시 게시글 작성 허용

        post = serializer.save(user=request.user)

        # 이미지 업로드 처리
        images = request.FILES.getlist('images')
        for image in images:
            PostImage.objects.create(post=post, image=image)

        return Response(PostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 게시글 상세 조회 / 수정 / 삭제
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'GET':
        post.view_count += 1
        post.save()
        serializer = PostDetailSerializer(post, context={'request': request})
        return Response(serializer.data)

    # 작성자 본인만 수정/삭제 가능
    if post.user != request.user:
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method in ['PUT', 'PATCH']:
        serializer = PostSerializer(
            post, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    post.delete()
    return Response({'message': '게시글이 삭제되었습니다.'})

# 게시글 이미지 삭제
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def post_image_delete(request, post_id, image_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.user != request.user:
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    image = get_object_or_404(PostImage, id=image_id, post=post)
    image.image.delete()  # 실제 파일 삭제
    image.delete()        # DB 삭제
    return Response({'message': '이미지가 삭제되었습니다.'})


# 게시글 이미지 추가
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_image_add(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    
    if post.user != request.user:
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    images = request.FILES.getlist('images')
    if not images:
        return Response(
            {'error': '이미지를 첨부해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    for image in images:
        PostImage.objects.create(post=post, image=image)
    
    from .serializers import PostImageSerializer
    return Response(
        PostImageSerializer(post.images.all(), many=True, context={'request': request}).data,
        status=status.HTTP_201_CREATED
    )

# 댓글 생성
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_create(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 댓글 수정 / 삭제
@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def comment_detail(request, post_id, comment_id):
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if comment.user != request.user:
        return Response(
            {'error': '권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    if request.method in ['PUT', 'PATCH']:
        serializer = CommentSerializer(
            comment, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    comment.delete()
    return Response({'message': '댓글이 삭제되었습니다.'})


# 좋아요 토글
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = PostLike.objects.get_or_create(
        post=post, user=request.user
    )
    if not created:
        like.delete()
        return Response({'message': '좋아요 취소', 'is_liked': False})
    return Response({'message': '좋아요', 'is_liked': True})


# 팔로우 토글
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_toggle(request, user_id):
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        return Response(
            {'error': '자기 자신을 팔로우할 수 없습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    follow, created = Follow.objects.get_or_create(
        follower=request.user, following=target_user
    )
    if not created:
        follow.delete()
        return Response({'message': '팔로우 취소', 'is_following': False})
    return Response({'message': '팔로우', 'is_following': True})


# 팔로우/팔로잉 목록
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def follow_list(request):
    following = Follow.objects.filter(follower=request.user)
    followers = Follow.objects.filter(following=request.user)
    return Response({
        'following_count': following.count(),
        'followers_count': followers.count(),
        'following': FollowSerializer(following, many=True).data,
        'followers': FollowSerializer(followers, many=True).data,
    })

# ============================================================
# 관리자 기능
# ============================================================
from config.permissions import IsAdminUser


# 관리자 - 전체 게시글 목록 조회
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_post_list(request):
    posts = Post.objects.all().order_by('-created_at')
    serializer = PostDetailSerializer(posts, many=True, context={'request': request})
    return Response(serializer.data)


# 관리자 - 게시글 강제 삭제
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def admin_post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.delete()
    return Response({'message': f'게시글 {post_id}번이 삭제되었습니다.'})


# 관리자 - 신뢰도 점수 수정
@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def admin_post_reliability(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    score = request.data.get('reliability_score')
    is_trusted = request.data.get('is_trusted')

    if score is not None:
        post.reliability_score = score
    if is_trusted is not None:
        post.is_trusted = is_trusted

    post.save()
    serializer = PostSerializer(post, context={'request': request})
    return Response(serializer.data)


# 관리자 - 신뢰도 높은 제보자 랭킹
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reporter_ranking(request):
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Avg

    User = get_user_model()

    ranking = User.objects.annotate(
        post_count=Count('posts'),
        avg_reliability=Avg('posts__reliability_score'),
        trusted_count=Count('posts', filter=__import__('django.db.models', fromlist=['Q']).Q(posts__is_trusted=True))
    ).filter(post_count__gt=0).order_by('-avg_reliability', '-post_count')[:20]

    result = [
        {
            'id': user.id,
            'username': user.username,
            'post_count': user.post_count,
            'avg_reliability': round(user.avg_reliability or 0, 2),
            'trusted_count': user.trusted_count,
        }
        for user in ranking
    ]
    return Response(result)


# ============================================================
# 공지사항
# ============================================================
from .models import Notice

# 공지사항 목록 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def notice_list(request):
    notices = Notice.objects.all()
    return Response([
        {
            'id': n.id,
            'title': n.title,
            'category': n.category,
            'is_pinned': n.is_pinned,
            'view_count': n.view_count,
            'created_at': n.created_at,
        }
        for n in notices
    ])


# 공지사항 상세 조회
@api_view(['GET'])
@permission_classes([AllowAny])
def notice_detail(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)
    notice.view_count += 1
    notice.save()
    return Response({
        'id': notice.id,
        'title': notice.title,
        'content': notice.content,
        'category': notice.category,
        'is_pinned': notice.is_pinned,
        'view_count': notice.view_count,
        'created_at': notice.created_at,
        'updated_at': notice.updated_at,
    })


# 관리자 - 공지사항 작성
@api_view(['POST'])
@permission_classes([IsAdminUser])
def notice_create(request):
    title = request.data.get('title')
    content = request.data.get('content')
    category = request.data.get('category', 'notice')
    is_pinned = request.data.get('is_pinned', False)

    if not title or not content:
        return Response(
            {'error': '제목과 내용을 입력해주세요.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    notice = Notice.objects.create(
        title=title,
        content=content,
        category=category,
        is_pinned=is_pinned,
    )
    return Response({
        'id': notice.id,
        'title': notice.title,
        'content': notice.content,
        'category': notice.category,
        'is_pinned': notice.is_pinned,
        'created_at': notice.created_at,
    }, status=status.HTTP_201_CREATED)


# 관리자 - 공지사항 수정/삭제
@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def notice_update(request, notice_id):
    notice = get_object_or_404(Notice, id=notice_id)

    if request.method in ['PUT', 'PATCH']:
        notice.title = request.data.get('title', notice.title)
        notice.content = request.data.get('content', notice.content)
        notice.category = request.data.get('category', notice.category)
        notice.is_pinned = request.data.get('is_pinned', notice.is_pinned)
        notice.save()
        return Response({
            'id': notice.id,
            'title': notice.title,
            'content': notice.content,
            'category': notice.category,
            'is_pinned': notice.is_pinned,
            'updated_at': notice.updated_at,
        })

    notice.delete()
    return Response({'message': '공지사항이 삭제되었습니다.'})