from rest_framework import permissions


class IsAuthorAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешает чтение всем, запись — авторизованным,
    редактирование/удаление — автору или администратору.
    """

    def has_permission(self, request, view):
        """Проверяет доступ к вьюсету."""
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Проверяет доступ к конкретному объекту."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
            or request.user.is_staff
        )
