from recipes.models import Follow


class AvatarMixin:
    def get_avatar(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class ImageUrlMixin:
    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None


class SubscriptionMixin:
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Follow.objects.filter(user=request.user, following=obj).exists()
