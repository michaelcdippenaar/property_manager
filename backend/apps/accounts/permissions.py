from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN


class IsAgentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.AGENT, User.Role.ADMIN)
        )


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.OWNER


class IsSupplier(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.SUPPLIER


class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.TENANT


class IsOwnerOrStaff(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in (User.Role.OWNER, User.Role.AGENT, User.Role.ADMIN)
        )
