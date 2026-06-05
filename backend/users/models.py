from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from core.constants import MAX_NAMES_LENGTH, EMAIL_LENGTH


class FoodgramUser(AbstractUser):
    """Модель пользователя."""
    username = models.CharField(
        max_length=MAX_NAMES_LENGTH,
        unique=True,
        verbose_name='Имя пользователя',
        validators=[UnicodeUsernameValidator()]
    )
    email = models.EmailField(
        unique=True,
        max_length=EMAIL_LENGTH,
        verbose_name='Почта'
    )
    first_name = models.CharField(
        max_length=MAX_NAMES_LENGTH,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_NAMES_LENGTH,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        upload_to='users/',
        verbose_name='Аватар'
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username
