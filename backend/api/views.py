from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from recipes.models import (
    Ingredient,
    Recipe,
    RecipeFavorites,
    RecipeIngredient,
    ShoppingCart,
    Tag,
)
from users.models import Follow
from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortRecipeSerializer,
    SubscribedUserSerializer,
    TagSerializer,
)


User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингредиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с тегами."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""

    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_shopping_list(self, request):
        ingredient_total = (
            RecipeIngredient.objects.filter(recipe__carts__user=request.user)
            .values(
                'ingredient__name',
                'ingredient__measurement_unit',
            )
            .annotate(total_amount=Sum('amount'))
        ).order_by('ingredient__name')
        return ingredient_total

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = recipe.short_link
        return Response({'short-link': short_link})

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        shopping_cart = self.get_shopping_list(request)
        if not shopping_cart:
            return Response(status=status.HTTP_404_NOT_FOUND)
        ingredients = [
            (
                f"{item['ingredient__name']} — "
                f"{item['total_amount']} "
                f"{item['ingredient__measurement_unit']}"
            )
            for item in shopping_cart
        ]
        content = '\n'.join(ingredients)
        response = HttpResponse(
            content.encode('utf-8'), content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.txt"'
        )
        return response

    def _add_item(self, request, recipe, model, lookup_kwargs):
        obj, created = model.objects.get_or_create(
            **lookup_kwargs
        )
        if not created:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = ShortRecipeSerializer(
            recipe, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_item(self, request, model, lookup_kwargs):
        deleted_count, _ = model.objects.filter(
            **lookup_kwargs
        ).delete()
        if deleted_count == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._add_item(
            request=request,
            recipe=recipe,
            model=ShoppingCart,
            lookup_kwargs={'user': request.user, 'recipe': recipe}
        )

    @shopping_cart.mapping.delete
    def delete_from_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._remove_item(
            model=ShoppingCart,
            request=request,
            lookup_kwargs={'user': request.user, 'recipe': recipe}
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._add_item(
            request=request,
            recipe=recipe,
            model=RecipeFavorites,
            lookup_kwargs={'favorites': request.user, 'recipe': recipe}
        )

    @favorite.mapping.delete
    def delete_from_favorites(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self._remove_item(
            model=RecipeFavorites,
            request=request,
            lookup_kwargs={'favorites': request.user, 'recipe': recipe}
        )

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer


class FoodgramUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""

    queryset = User.objects.all()
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = LimitOffsetPagination
    permission_classes = [AllowAny]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request,):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request):
        serializer = AvatarSerializer(
            instance=request.user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save(update_fields=['avatar'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
    )
    def subscriptions(self, request):
        followings = User.objects.filter(
            follow__user=request.user
        ).prefetch_related(
            'created_recipes'
        )
        paginator = self.pagination_class()
        recipes_limit = request.query_params.get('recipes_limit')
        context = self.get_serializer_context()
        context['recipes_limit'] = recipes_limit
        page = paginator.paginate_queryset(followings, request, view=self)
        page = self.paginate_queryset(followings)
        if page is not None:
            serializer = SubscribedUserSerializer(
                page, context=context, many=True
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscribedUserSerializer(
            followings, context=context, many=True
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        following = get_object_or_404(User, pk=id)
        if following == request.user:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        subscribe, created = Follow.objects.get_or_create(
            user=request.user, following=following
        )
        if not created:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        recipes_limit = request.query_params.get('recipes_limit')
        context = self.get_serializer_context()
        context['recipes_limit'] = recipes_limit
        serializer = SubscribedUserSerializer(following, context=context)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscription(self, request, id=None):
        following = get_object_or_404(User, pk=id)
        deleted_count, _ = Follow.objects.filter(
            user=request.user, following=following
        ).delete()
        if deleted_count == 0:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
