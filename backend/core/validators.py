from recipes.models import Ingredient, RecipeIngredient
from rest_framework import serializers


def ingredient_validation(ingredients, recipe):
    recipe_ingredients = []
    seen_ingredient_ids = set()
    for ingredient_data in ingredients:
        ingredient_id = ingredient_data['id']
        if ingredient_id in seen_ingredient_ids:
            raise serializers.ValidationError(
                f'Ингредиент с id {ingredient_id} указан более одного раза'
            )
        seen_ingredient_ids.add(ingredient_id)
        try:
            ingredient = Ingredient.objects.get(pk=ingredient_id)
        except Ingredient.DoesNotExist:
            raise serializers.ValidationError(
                f'Ингредиент с id {ingredient_id} не найден'
            )
        amount = ingredient_data['amount']
        if not amount or amount < 1:
            raise serializers.ValidationError(
                'Поле "amount" обязательно для заполнения, '
                'должно быть положительным числом'
            )
        recipe_ingredients.append(
            RecipeIngredient(
                ingredient=ingredient, recipe=recipe, amount=amount
            )
        )
    return recipe_ingredients


def validate_tags(tags):
    unique_tags = set(tags)
    if len(tags) != len(unique_tags):
        raise serializers.ValidationError('Указаны повторяющиеся теги')
    return unique_tags
