from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """관리자(staff) 전용 권한"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff