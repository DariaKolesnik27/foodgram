from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from api.views import (
    FoodgramUserViewSet,
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet,
    short_link_redirect,
)


router = routers.DefaultRouter()
router.register(r'users', FoodgramUserViewSet, basename='user')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auth/', include('djoser.urls.authtoken')),
    path('s/<str:short_link>/', short_link_redirect),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
