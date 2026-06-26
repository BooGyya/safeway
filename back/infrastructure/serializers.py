from rest_framework import serializers
from .models import TrafficLight, Facility, Elevator, SupportCenter


class TrafficLightSerializer(serializers.ModelSerializer):
    pedestrian_green_time = serializers.SerializerMethodField()

    class Meta:
        model = TrafficLight
        fields = [
            'id', 'sido', 'sigungu', 'road_nm',
            'lat', 'lng',
            'sgn_asp_ordr', 'sgn_asp_time',
            'has_audio', 'has_remndr', 'is_operating',
            'pedestrian_green_time',
        ]

    def get_pedestrian_green_time(self, obj):
        return obj.get_pedestrian_green_time()


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            'id', 'name', 'facility_type',
            'sido', 'sigungu', 'address',
            'lat', 'lng', 'is_available',
        ]


class ElevatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Elevator
        fields = [
            'id', 'building_nm', 'sido', 'sigungu',
            'address', 'lat', 'lng',
            'elevator_type', 'is_operating', 'install_place',
        ]


class SupportCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportCenter
        fields = [
            'id', 'name', 'sido', 'sigungu',
            'address', 'lat', 'lng',
            'phone', 'is_operating',
        ]