import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from core.constants import EMAIL_LENGTH, MAX_IMAGE_SIZE_MB, MAX_NAMES_LENGTH
from core.mixins import AvatarMixin, ImageUrlMixin, SubscriptionMixin
from core.validators import ingredient_validation, validate_tags
from recipes.models import (
    Follow, Ingredient, Recipe, RecipeIngredient, RecipeShortLink, Tag
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


class ShortRecipeSerializer(serializers.ModelSerializer, ImageUrlMixin):
    """Сериализатор для краткого отображения рецептов."""

    image = serializers.SerializerMethodField(
        'get_image', read_only=True,
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


class FoodgramCreateUserSerializer(serializers.ModelSerializer):
    """Сериализатор для POST/PATCH-запросов модели FoodgramUser."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH, required=True)
    username = serializers.CharField(
        max_length=MAX_NAMES_LENGTH,
        required=True,
    )
    first_name = serializers.CharField(
        max_length=MAX_NAMES_LENGTH, required=True
    )
    last_name = serializers.CharField(
        max_length=MAX_NAMES_LENGTH, required=True
    )

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        username = data.get('username')
        email = data.get('email')
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': 'Пользователь с такой почтой уже существует.'
            })
        elif User.objects.filter(username=username).exists():
            raise serializers.ValidationError({
                'username': 'Пользователь с таким username уже существует.'
            })
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class FoodgramReadUserSerializer(
    serializers.ModelSerializer, AvatarMixin, SubscriptionMixin
):
    """Сериализатор для  GET-запросов модели FoodgramUser."""

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


class RecipeReadSerializer(serializers.ModelSerializer, ImageUrlMixin):
    """Сериализатор для GET-запросов модели Recipe."""

    image = serializers.SerializerMethodField(
        'get_image',
        read_only=True,
    )
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField('get_ingredients')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = FoodgramReadUserSerializer()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'text', 'cooking_time',
            'image', 'tags', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.favorites.filter(pk=user.pk).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.shopping_cart.filter(pk=user.pk).exists()
        return False

    def get_ingredients(self, obj):
        recipe_ingredients = obj.recipe_ingredients.all()
        return [
            {
                'id': ri.ingredient.id,
                'name': ri.ingredient.name,
                'measurement_unit': ri.ingredient.measurement_unit,
                'amount': ri.amount
            }
            for ri in recipe_ingredients
        ]


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для POST/PATCH-запросов модели Recipe."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        allow_null=False,
        allow_empty=False,
    )
    ingredients = serializers.ListField(
        child=serializers.DictField(
            child=serializers.IntegerField()
        ),
        allow_null=False,
        allow_empty=False,
    )
    image = Base64ImageField(required=True)
    cooking_time = serializers.IntegerField(min_value=1)
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Recipe
        fields = (
            'name', 'text', 'cooking_time', 'tags',
            'ingredients', 'image', 'author'
        )

    def create(self, validated_data):
        if (
            'ingredients' not in self.initial_data
            or 'tags' not in self.initial_data
        ):
            raise serializers.ValidationError(
                'Заполните все обязательные поля'
            )
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        unique_tags = validate_tags(tags)
        with transaction.atomic():
            recipe = Recipe.objects.create(**validated_data)
            recipe_ingredients = ingredient_validation(ingredients, recipe)
            RecipeIngredient.objects.bulk_create(recipe_ingredients)
            recipe.tags.set(unique_tags)
            return recipe

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance.name = validated_data.get('name', instance.name)
            instance.text = validated_data.get('text', instance.text)
            instance.cooking_time = validated_data.get(
                'cooking_time', instance.cooking_time
            )
            instance.image = validated_data.get('image', instance.image)
            instance.recipe_ingredients.all().delete()

            if 'ingredients' not in validated_data:
                raise serializers.ValidationError(
                    'Поле "Ингредиенты" обязательно для заполнения'
                )
            ingredients = validated_data.pop('ingredients')
            recipe_ingredients = ingredient_validation(
                ingredients, instance
            )
            RecipeIngredient.objects.bulk_create(recipe_ingredients)

            if 'tags' not in validated_data:
                raise serializers.ValidationError(
                    'Поле "Теги" обязательно для заполнения'
                )
            tags = validated_data.pop('tags')
            unique_tags = validate_tags(tags)
            instance.tags.set(unique_tags)

            instance.save()
            return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class SubscribedUserSerializer(
    serializers.ModelSerializer, AvatarMixin, SubscriptionMixin
):
    """Сериализатор для получения подписок пользователя."""

    recipes = serializers.SerializerMethodField('get_recipes')
    recipes_count = serializers.SerializerMethodField('get_recipes_count')
    is_subscribed = serializers.SerializerMethodField('get_is_subscribed')
    avatar = serializers.SerializerMethodField(
        'get_avatar',
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'avatar',
            'is_subscribed', 'recipes', 'recipes_count'
        ]

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


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для POST-запросов модели Follow."""

    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )
    following = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
    )

    class Meta:
        model = Follow
        fields = '__all__'
        validators = [
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=['user', 'following']
            )
        ]

    def validate_following(self, value):
        request_user = self.context['request'].user
        if request_user == value:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя.'
            )

        return value

    def to_representation(self, instance):
        return SubscribedUserSerializer(
            instance.following, context=self.context
        ).data


class ShortLinkSerializer(serializers.ModelSerializer):
    """Сериализатор для GET-запросов модели RecipeShortLink."""

    class Meta:
        model = RecipeShortLink
        fields = ('short_link',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['short-link'] = data.pop('short_link')
        return data
