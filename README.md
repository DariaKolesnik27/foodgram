# Foodgram 
  
Проект Foodgram - это социальная сеть для любителей кулинарии. Пользователи имеют возможность публиковать свои рецепты, могут подписываться на авторов, добавлять блюда в «Избранное», формировать список покупок (с возможностью скачивания списка покупок в формате .txt). Проект реализует полный CRUD для рецептов, ингредиентов и тегов, систему подписок, избранное и корзину. Реализована аутентификация через Djoser, разграничение прав доступа и фильтрация данных.
  
## Технологии  

**Backend:** 
- Python 3.12.7  
- Django
- django-filter
- djangorestframework
- djoser
**Работа с данными:**
- PostgreSQL
- psycopg2-binary
**Медиафайлы:** 
- pillow
**Контейнеризация:**
- Docker
- Docker Compose
**Frontend:** 
- React
  
## Запуск контейнеров 

Проект разворачивается с помощью Docker Compose.

1. Создайте файл `.env` в корне проекта в соответствии с шаблоном `.env.example`. Отредактируйте файл `.env`, подставив свои реальные значения для переменных окружения.
Файл `.env` не должен попадать в репозиторий — убедитесь, что он добавлен в `.gitignore`.


2. Соберите и запустите контейнеры. Выполните команду из директории infra:

```
docker compose -f docker-compose.yml up -d --build
```

3. Примените миграции и соберите статику
```
docker compose -f docker-compose.yml exec backend python manage.py migrate
```

```
docker compose -f docker-compose.yml exec backend python manage.py collectstatic --noinput
```

4. Для остановки всех контейнеров:
```
docker compose -f docker-compose.yml down
```

## Ссылка на развернутый проект
Проект доступен по ссылке: https://foxkitchen.ddns.net/

## Спецификация   
Спецификация доступна в YAML‑файле foodgram/docs/openapi-schema.yml, а также через веб‑интерфейс.
  
## Авторы проекта  
Проект разработан: 
- [DariaKolesnik27](https://github.com/DariaKolesnik27)
