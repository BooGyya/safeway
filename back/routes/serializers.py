from rest_framework import serializers
from .models import Route, RouteFavorite, RouteHistory


class RouteSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Route
        fields = [
            'id', 'username',
            'origin_name', 'origin_lat', 'origin_lng',
            'dest_name', 'dest_lat', 'dest_lng',
            'distance', 'duration', 'safety_score',
            'waypoints', 'weather_applied',
            'transport_type',
            'created_at',
        ]
        read_only_fields = ['id', 'username', 'created_at']


class RouteFavoriteSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = RouteFavorite
        fields = ['id', 'route', 'nickname', 'created_at']
        read_only_fields = ['id', 'created_at']


class RouteHistorySerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = RouteHistory
        fields = ['id', 'route', 'used_at']
        read_only_fields = ['id', 'used_at']