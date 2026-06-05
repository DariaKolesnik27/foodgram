from django.contrib import admin

from .models import Ingredient, Recipe, Tag


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('mame',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('favorites')

    def favorites_count(self, obj):
        return obj.favorites.count()


admin.site.register(Tag)
