from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from core.mixins import AvatarMixin, ImageUrlMixin, SubscriptionMixin
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)
from .serializers_fields import Base64ImageField


User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для создания аватара."""

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class ShortRecipeSerializer(ImageUrlMixin, serializers.ModelSerializer):
    """Сериализатор для краткого отображения рецептов."""

    image = serializers.SerializerMethodField(
        'get_image',
        read_only=True,
    )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class FoodgramUserSerializer(
    AvatarMixin, SubscriptionMixin, serializers.ModelSerializer
):
    """Сериализатор для модели FoodgramUser."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField(
        'get_avatar',
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
        )


class RecipeIngredientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer, ImageUrlMixin):
    """Сериализатор для GET-запросов модели Recipe."""

    image = serializers.SerializerMethodField(
        'get_image',
        read_only=True,
    )
    tags = TagSerializer(many=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients', many=True, read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True, default=False
    )
    author = FoodgramUserSerializer()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'name',
            'text',
            'cooking_time',
            'image',
            'tags',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для POST/PATCH-запросов модели Recipe."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        allow_null=False,
        allow_empty=False,
    )
    ingredients = RecipeIngredientSerializer(many=True)
    image = Base64ImageField(required=True)
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Recipe
        fields = (
            'name',
            'text',
            'cooking_time',
            'tags',
            'ingredients',
            'image',
            'author',
        )

    def validate(self, data):
        tags = data.get('tags')
        ingredients = data.get('ingredients')
        if not tags:
            raise serializers.ValidationError(
                'Список тегов не может быть пустым'
            )
        unique_tags = set(tags)
        if len(tags) != len(unique_tags):
            raise serializers.ValidationError('Указаны повторяющиеся теги')
        if not ingredients:
            raise serializers.ValidationError(
                'Список ингредиентов не может быть пустым.'
            )
        seen_ids = set()
        for item in ingredients:
            ingredient_id = item['ingredient'].id
            if ingredient_id in seen_ids:
                raise serializers.ValidationError(
                    f'Ингредиент с ID {ingredient_id} указан более одного раза'
                )
            seen_ids.add(ingredient_id)
        return data

    def _save_ingredients(self, recipe, ingredients_data):
        ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients)

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients)
        recipe.tags.set(tags)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self._save_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class SubscribedUserSerializer(FoodgramUserSerializer):
    """Сериализатор для получения подписок пользователя."""

    recipes = serializers.SerializerMethodField('get_recipes')
    recipes_count = serializers.SerializerMethodField('get_recipes_count')

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        limit = self.context['recipes_limit']
        if limit is not None:
            limit = int(limit)
        recipes = obj.created_recipes.all().prefetch_related(
            'ingredients', 'tags'
        )
        return ShortRecipeSerializer(recipes[:limit], many=True).data

    def get_recipes_count(self, obj):
        return obj.created_recipes.count()
