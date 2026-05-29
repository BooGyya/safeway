from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Post, Comment, PostLike, Follow
from .serializers import (
    PostSerializer, PostDetailSerializer,
    CommentSerializer, FollowSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()


# 게시글 목록 조회 / 생성
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedOrReadOnly])
def post_list(request):
    if request.method == 'GET':
        # 정렬 기준 (신뢰도순 / 최신순 / 팔로우 우선)
        sort = request.query_params.get('sort', 'latest')
        posts = Post.objects.all()

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

        serializer = PostSerializer(
            posts, many=True, context={'request': request}
        )
        return Response(serializer.data)

    # 게시글 생성
    serializer = PostSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
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