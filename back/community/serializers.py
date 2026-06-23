from rest_framework import serializers
from .models import Post, Comment, PostLike, Follow, PostImage
from django.conf import settings

class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ['id', 'image', 'created_at']

class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'username', 'user_id', 'content',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'user_id', 'created_at', 'updated_at']


class PostSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'username', 'user_id', 'title', 'content',
            'category', 'latitude', 'longitude', 'address',
            'reliability_score', 'is_trusted', 'view_count',
            'like_count', 'comment_count', 'is_liked', 'is_following',
            'images',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'username', 'user_id', 'reliability_score',
            'is_trusted', 'view_count', 'created_at', 'updated_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return PostLike.objects.filter(
                post=obj,
                user=request.user
            ).exists()
        return False

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .models import Follow
            return Follow.objects.filter(
                follower=request.user,
                following=obj.user
            ).exists()
        return False


class PostDetailSerializer(PostSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ['comments']


class FollowSerializer(serializers.ModelSerializer):
    follower_username = serializers.CharField(
        source='follower.username',
        read_only=True
    )
    following_username = serializers.CharField(
        source='following.username',
        read_only=True
    )

    class Meta:
        model = Follow
        fields = [
            'id', 'follower_username',
            'following_username', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']