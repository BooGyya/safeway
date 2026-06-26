from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )
    nickname = serializers.CharField(required=True)
    terms_agreed = serializers.BooleanField(required=True)
    privacy_agreed = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'nickname', 'name', 'phone',
            'user_type', 'walk_speed',
            'terms_agreed', 'privacy_agreed',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password': '비밀번호가 일치하지 않습니다.'}
            )
        if not attrs.get('terms_agreed'):
            raise serializers.ValidationError(
                {'terms_agreed': '이용약관에 동의해주세요.'}
            )
        if not attrs.get('privacy_agreed'):
            raise serializers.ValidationError(
                {'privacy_agreed': '개인정보처리방침에 동의해주세요.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'nickname', 'name', 'phone',
            'user_type', 'walk_speed',
            'profile_image', 'font_size',
            'voice_type', 'voice_volume',
            'sos_number', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password': '새 비밀번호가 일치하지 않습니다.'}
            )
        return attrs