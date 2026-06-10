import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from core.constants import MAX_IMAGE_SIZE_MB
from core.mixins import AvatarMixin, ImageUrlMixin, SubscriptionMixin
from core.validators import prepare_ingredients_list, get_unique_tags
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag,
)


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Сериализатор для работы с изображениями."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)

    def validate_file(self, value):
        if value.size > 1024 * 1024 * MAX_IMAGE_SIZE_MB:
            raise serializers.ValidationError(
                'Размер файла не должен превышать 10MB'
            )
        return value


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


class RecipeIngredientSerializer(serializers.Serializer):
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField(min_value=1)
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

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        unique_tags = get_unique_tags(tags)
        validated_data['author'] = self.context['request'].user
        recipe = Recipe.objects.create(**validated_data)
        recipe_ingredients = prepare_ingredients_list(ingredients, recipe)
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
        recipe.tags.set(unique_tags)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags', None)
        instance = super().update(instance, validated_data)
        if not tags:
            raise serializers.ValidationError('Поле "Теги" обязательно')
        unique_tags = get_unique_tags(tags)
        instance.tags.clear()
        instance.tags.set(unique_tags)
        if not ingredients:
            raise serializers.ValidationError('Поле "Ингредиенты" обязательно')
        recipe_ingredients = prepare_ingredients_list(
            ingredients, instance
        )
        instance.recipe_ingredients.all().delete()
        RecipeIngredient.objects.bulk_create(recipe_ingredients)
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
