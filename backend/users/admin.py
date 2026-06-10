from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count

from .models import Follow


User = get_user_model()

UserAdmin.list_display += ('recipes_count',)
UserAdmin.search_fields += ('username', 'email')


class UserWithRecipeCountAdmin(UserAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipes_count=Count('created_recipes')
        )

    def recipes_count(self, obj):
        return obj.recipes_count


admin.site.register(User, UserWithRecipeCountAdmin)
admin.site.register(Follow)
admin.site.unregister(Group)
