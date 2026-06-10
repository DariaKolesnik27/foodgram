from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from core.constants import EMAIL_LENGTH, MAX_NAMES_LENGTH


class FoodgramUser(AbstractUser):
    """Модель пользователя."""

    username = models.CharField(
        max_length=MAX_NAMES_LENGTH,
        unique=True,
        verbose_name='Имя пользователя',
        validators=[UnicodeUsernameValidator()],
    )
    email = models.EmailField(
        unique=True, max_length=EMAIL_LENGTH, verbose_name='Почта'
    )
    first_name = models.CharField(
        max_length=MAX_NAMES_LENGTH, verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_NAMES_LENGTH, verbose_name='Фамилия'
    )
    avatar = models.ImageField(upload_to='users/', verbose_name='Аватар')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Follow(models.Model):
    """Модель подписки пользователя на другого пользователя."""

    user = models.ForeignKey(
        FoodgramUser,
        on_delete=models.CASCADE,
        related_name='follow',
    )
    following = models.ForeignKey(
        FoodgramUser,
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
