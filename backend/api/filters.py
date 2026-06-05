from django.db.models import Exists, OuterRef
import django_filters as filters
from django_filters import rest_framework

from recipes.models import Ingredient, Recipe, RecipeFavorites


class NumberInFilter(filters.BaseInFilter, rest_framework.NumberFilter):
    pass


class RecipeFilter(rest_framework.FilterSet):
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
    )
    author = filters.NumberFilter(
        field_name='author__id',
    )
    is_favorited = filters.ChoiceFilter(
        choices=[('0', False), ('1', True)],
        method='filter_is_favorited',
    )
    is_in_shopping_cart = filters.ChoiceFilter(
        choices=[('0', False), ('1', True)],
        method='filter_is_in_shopping_cart',
    )

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated:
            subquery = Exists(
                RecipeFavorites.objects.filter(
                    recipe=OuterRef('pk'),
                    favorites=user
                )
            )
            if value:
                return queryset.filter(subquery)
            return queryset.filter(~subquery)
        if value:
            return queryset.none()
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if user.is_authenticated:
            subquery = Exists(
                user.shopping_cart_recipes.filter(pk=OuterRef('pk'))
            )
            if value:
                return queryset.filter(subquery)
            return queryset.filter(~subquery)
        if value:
            return queryset.none()
        return queryset

    class Meta:
        model = Recipe
        fields = ['tags', 'is_favorited', 'author', 'is_in_shopping_cart']


class IngredientFilter(rest_framework.FilterSet):
    name = filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ['name']
