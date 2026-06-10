from django.contrib import admin
from django.db.models import Count

from .models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeFavorites,
    Tag,
    ShoppingCart
)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'recipes_count')
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipes_count=Count('ingredient_recipes')
        )

    def recipes_count(self, obj):
        return obj.recipes_count


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'favorites_count')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    inlines = [RecipeIngredientInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            favorites_count=Count('favorites')
        )

    def favorites_count(self, obj):
        return obj.favorites_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'recipes_count')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipes_count=Count('recipes')
        )

    def recipes_count(self, obj):
        return obj.recipes_count


admin.site.register(ShoppingCart)
admin.site.register(RecipeFavorites)
