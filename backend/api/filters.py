import django_filters.rest_framework as filters

from recipes.models import Ingredient, Recipe


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class RecipeFilter(filters.FilterSet):
    tags = filters.AllValuesMultipleFilter(
        field_name='tags__slug',
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited',)
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
    )

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated or value is None:
            return queryset
        method = queryset.filter if value else queryset.exclude
        return method(recipe_favorites__favorites=user)

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if not user.is_authenticated or value is None:
            return queryset
        method = queryset.filter if value else queryset.exclude
        return method(shopping_cart=user)

    class Meta:
        model = Recipe
        fields = ['tags', 'is_favorited', 'author', 'is_in_shopping_cart']


class IngredientFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
