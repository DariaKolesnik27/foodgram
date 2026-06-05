import textwrap

from django.contrib.auth import get_user_model
from django.db import models

from core.constants import (
    MAX_LINK_LENGTH,
    MAX_RECIPE_NAMES_LENGTH,
    MAX_SLUG_LENGTH,
    MAX_TAGS_LENGTH,
    MAX_UNIT_LENGTH,
    TEXT_WIDTH,
)


User = get_user_model()


class TagIngredientAbstractModel(models.Model):
    """Абстрактная модель."""

    name = models.CharField(
        unique=True,
        max_length=MAX_TAGS_LENGTH,
        verbose_name='Название',
    )

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return textwrap.shorten(self.name, width=TEXT_WIDTH, placeholder='...')


class Tag(TagIngredientAbstractModel):
    """Модель тега."""

    slug = models.SlugField(
        max_length=MAX_SLUG_LENGTH,
        unique=True,
        verbose_name='Слаг',
    )

    class Meta(TagIngredientAbstractModel.Meta):
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'


class Ingredient(TagIngredientAbstractModel):
    """Модель ингредиента."""

    measurement_unit = models.CharField(
        max_length=MAX_UNIT_LENGTH, verbose_name='Единица измерения'
    )

    class Meta(TagIngredientAbstractModel.Meta):
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'


class Recipe(models.Model):
    """Модель рецепта."""

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
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    favorites = models.ManyToManyField(
        User,
        through='RecipeFavorites',
        related_name='favorite_recipes',
        verbose_name='Избранное',
        blank=True,
    )
    shopping_cart = models.ManyToManyField(
        User, related_name='shopping_cart_recipes', blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

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
    )

    class Meta:
        verbose_name = 'Количество ингредиента в рецепте'
        verbose_name_plural = 'Количества ингредиентов в рецептах'
        unique_together = ('recipe', 'ingredient')

    def __str__(self):
        return (
            f'{self.ingredient.name}: {self.amount} '
            f'{self.ingredient.measurement_unit}'
        )


class RecipeFavorites(models.Model):
    """Промежуточная модель рецептов, добавленных в избранное."""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='recipe_favorites'
    )
    favorites = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites_recipe'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'favorites'], name='unique_favorites'
            ),
        ]


class Follow(models.Model):
    """Модель подписки пользователя на другого пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follow',
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follows',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'following'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('following')),
                name='cant_follow_to_yourself',
            ),
        ]


class RecipeShortLink(models.Model):
    """Модель коротких ссылок на рецепты."""

    recipe = models.OneToOneField(
        Recipe,
        on_delete=models.CASCADE,
        related_name='short_link',
        verbose_name='Рецепт',
    )
    short_link = models.CharField(
        max_length=MAX_LINK_LENGTH, unique=True, verbose_name='Короткая ссылка'
    )

    class Meta:
        verbose_name = 'Короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def __str__(self):
        return f'Короткая ссылка для рецепта - {self.recipe.name}'
