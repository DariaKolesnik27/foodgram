import base64

from django.core.files.base import ContentFile
from rest_framework import serializers

from core.constants import MAX_IMAGE_SIZE_MB


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
