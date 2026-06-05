import uuid

from core.constants import MAX_LINK_LENGTH
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from recipes.models import (
    Follow,
    Ingredient,
    Recipe,
    RecipeFavorites,
    RecipeShortLink,
    Tag,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorAdminOrReadOnly
from .serializers import (
    AvatarSerializer,
    FollowSerializer,
    FoodgramCreateUserSerializer,
    FoodgramReadUserSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortLinkSerializer,
    ShortRecipeSerializer,
    SubscribedUserSerializer,
    TagSerializer,
)

User = get_user_model()


def short_link_redirect(request, short_link):
    short_link = get_object_or_404(RecipeShortLink, short_link=short_link)
    return redirect(f'/recipes/{short_link.recipe.id}/')


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
    permission_classes = [IsAuthorAdminOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_shopping_list(self, request):
        ingredient_total = (
            Recipe.objects.filter(shopping_cart=request.user)
            .values(
                'recipe_ingredients__ingredient__name',
                'recipe_ingredients__ingredient__measurement_unit',
            )
            .annotate(total_amount=Sum('recipe_ingredients__amount'))
        )
        return ingredient_total

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link_obj, created = RecipeShortLink.objects.get_or_create(
            recipe=recipe,
            defaults={'short_link': uuid.uuid4().hex[:MAX_LINK_LENGTH]}
        )
        serializer = ShortLinkSerializer(
            short_link_obj, context={'request': request}
        )
        return Response(serializer.data)

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
                f'{item['recipe_ingredients__ingredient__name']} — '
                f'{item['total_amount']} '
                f'{item['recipe_ingredients__ingredient__measurement_unit']}'
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

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if request.user.shopping_cart_recipes.filter(
                id=recipe.id
            ).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            request.user.shopping_cart_recipes.add(recipe)
            serializer = ShortRecipeSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not request.user.shopping_cart_recipes.filter(
                id=recipe.id
            ).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            request.user.shopping_cart_recipes.remove(recipe)
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='favorite',
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if RecipeFavorites.objects.filter(
                favorites=request.user, recipe=recipe
            ).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            RecipeFavorites.objects.create(
                favorites=request.user, recipe=recipe
            )
            serializer = ShortRecipeSerializer(
                recipe, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            try:
                favorite = RecipeFavorites.objects.get(
                    favorites=request.user, recipe=recipe
                )
                favorite.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except RecipeFavorites.DoesNotExist:
                return Response(
                    {'detail': 'Рецепт не в избранном'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class FoodgramUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователями."""

    queryset = User.objects.all()
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [AllowAny()]
        else:
            return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'me'):
            return FoodgramReadUserSerializer
        elif self.action in ('set_password'):
            return SetPasswordSerializer
        return FoodgramCreateUserSerializer

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request):
        if request.method == 'PUT':
            if 'avatar' not in request.data:
                return Response(
                    {'error': 'Поле avatar обязательно для загрузки'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = AvatarSerializer(
                instance=request.user,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'DELETE':
            if request.user.avatar:
                request.user.avatar.delete(save=False)
                request.user.avatar = None
                request.user.save(update_fields=['avatar'])
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_404_NOT_FOUND)

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
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe',
    )
    def subscribe(self, request, id=None):
        following = get_object_or_404(User, pk=id)
        recipes_limit = request.query_params.get('recipes_limit')
        if request.method == 'POST':
            context = self.get_serializer_context()
            context['recipes_limit'] = recipes_limit
            serializer = FollowSerializer(
                data={'following': following.id}, context=context
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscription = Follow.objects.filter(
                user=request.user, following=following
            ).first()
            if subscription:
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(status=status.HTTP_400_BAD_REQUEST)
