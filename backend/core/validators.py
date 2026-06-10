from rest_framework import serializers

from recipes.models import RecipeIngredient


def prepare_ingredients_list(ingredients, recipe):
    if not ingredients:
        raise serializers.ValidationError(
            'Список ингредиентов не может быть пустым.'
        )
    seen_ids = set()
    for item in ingredients:
        ingredient_id = item['ingredient'].id
        if ingredient_id in seen_ids:
            raise serializers.ValidationError(
                f'Ингредиент с ID {ingredient_id} указан более одного раза.'
            )
        seen_ids.add(ingredient_id)
    return [
        RecipeIngredient(
            recipe=recipe,
            ingredient=item['ingredient'],
            amount=item['amount']
        )
        for item in ingredients
    ]


def get_unique_tags(tags):
    if not tags:
        raise serializers.ValidationError('Не указаны теги')
    unique_tags = set(tags)
    if len(tags) != len(unique_tags):
        raise serializers.ValidationError('Указаны повторяющиеся теги')
    return unique_tags
