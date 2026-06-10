from django.http import Http404
from django.shortcuts import redirect

from .models import Recipe


def short_link_redirect(request, short_link):
    try:
        recipe = Recipe.objects.get(short_link=short_link)
        return redirect(f'/recipes/{recipe.id}/')
    except Recipe.DoesNotExist:
        raise Http404("Рецепт по этой короткой ссылке не найден")
