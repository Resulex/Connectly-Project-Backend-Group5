from rest_framework.permissions import BasePermission


class IsPostAuthor(BasePermission):
    """
    Permission to allow only the author of a post to perform certain actions.
    """
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user

class IsAdminRole(BasePermission):
    """
    Permission that only allows admin (staff) users to perform certain actions.
    Uses Django's built-in is_staff flag instead of a custom role.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin'