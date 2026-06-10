from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Разрешает чтение всем, редактирование/удаление — автору."""

    def has_object_permission(self, request, view, obj):
        """Проверяет доступ к конкретному объекту."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )
