import textwrap
import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Exists, OuterRef, Value

from core.constants import (
    MAX_LINK_LENGTH,
    MAX_RECIPE_NAMES_LENGTH,
    MAX_SLUG_LENGTH,
    MAX_TAGS_LENGTH,
    MAX_UNIT_LENGTH,
    MAX_VALUE,
    MIN_VALUE,
    TEXT_WIDTH,
)


User = get_user_model()


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(
        unique=True,
        max_length=MAX_TAGS_LENGTH,
        verbose_name='Название',
    )
    slug = models.SlugField(
        max_length=MAX_SLUG_LENGTH,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return textwrap.shorten(self.name, width=TEXT_WIDTH, placeholder='...')


class Ingredient(models.Model):
    """Модель ингредиента."""

    name = models.CharField(
        max_length=MAX_RECIPE_NAMES_LENGTH,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=MAX_UNIT_LENGTH, verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        unique_together = ('name', 'measurement_unit')

    def __str__(self):
        return textwrap.shorten(self.name, width=TEXT_WIDTH, placeholder='...')


class ShoppingCartFavoritesAbstractModel(models.Model):
    """Абстрактная модель для корзины и избранного."""

    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='%(model_name)s_recipes'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='%(model_name)s_users'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'user'], name='unique_%(model_name)s'
            ),
        ]


class ShoppingCart(ShoppingCartFavoritesAbstractModel):

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class RecipeFavorites(ShoppingCartFavoritesAbstractModel):
    """Промежуточная модель рецептов, добавленных в избранное."""

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'


class RecipeQuerySet(models.QuerySet):
    def in_collection(self, user):
        if user and user.is_authenticated:
            is_favorited_subquery = Exists(
                RecipeFavorites.objects.filter(
                    recipe=OuterRef('pk'),
                    user=user
                )
            )
            is_in_cart_subquery = Exists(
                ShoppingCart.objects.filter(
                    recipe=OuterRef('pk'),
                    user=user
                )
            )
        else:
            is_favorited_subquery = Value(False)
            is_in_cart_subquery = Value(False)
        return self.annotate(
            is_favorited=is_favorited_subquery,
            is_in_shopping_cart=is_in_cart_subquery
        )


class Recipe(models.Model):
    """Модель рецепта."""

    objects = RecipeQuerySet.as_manager()
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_recipes',
        verbose_name='Автор',
    )
    name = models.CharField(
        max_length=MAX_RECIPE_NAMES_LENGTH,
        verbose_name='Название',
    )
    image = models.ImageField(upload_to='recipes/', verbose_name='Картинка')
    text = models.TextField(
        verbose_name='Описание',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Тег'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE)
        ]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    shopping_cart = models.ManyToManyField(
        User,
        through='ShoppingCart',
        related_name='cart_items',
        verbose_name='Корзина'
    )
    favorites = models.ManyToManyField(
        User,
        through='RecipeFavorites',
        related_name='favorite_recipes',
        verbose_name='Избранное',
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    short_link = models.CharField(
        max_length=MAX_LINK_LENGTH,
        unique=True,
        blank=True,
        null=False,
        verbose_name='Короткая ссылка'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if not self.short_link and not self.pk:
            while True:
                link = uuid.uuid4().hex[:MAX_LINK_LENGTH]
                if not Recipe.objects.filter(short_link=link).exists():
                    self.short_link = link
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return textwrap.shorten(self.name, width=TEXT_WIDTH, placeholder='...')


class RecipeIngredient(models.Model):
    """
    Промежуточная модель для связи рецептов с ингредиентами.
    Содержит дополнительную информацию о количестве ингредиентов.
    """

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name='ingredient_recipes'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE)
        ]
    )

    class Meta:
        verbose_name = 'Количество ингредиента в рецепте'
        verbose_name_plural = 'Количества ингредиентов в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'], name='unique_ingredients'
            ),
        ]

    def __str__(self):
        return (
            f'{self.ingredient.name}: {self.amount} '
            f'{self.ingredient.measurement_unit}'
        )
