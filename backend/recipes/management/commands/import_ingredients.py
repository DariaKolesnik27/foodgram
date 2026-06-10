import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Импорт данных из CSV файла'
    data_dir = settings.BASE_DIR / 'data'

    def handle(self, *args, **options):
        try:
            path = self.data_dir / 'ingredients.csv'
            with open(path, encoding='utf-8') as f:
                reader = csv.reader(f)
                ingredients = []
                for row in reader:
                    if len(row) >= 2:
                        name = row[0].strip()
                        unit = row[1].strip()

                        if name and unit:
                            ingredients.append(Ingredient(
                                name=name,
                                measurement_unit=unit
                            ))
                created_ingredients = Ingredient.objects.bulk_create(
                    ingredients, ignore_conflicts=True
                )
                count = len(created_ingredients)
            self.stdout.write(
                self.style.SUCCESS(f'Успешно обработано: {count} записей.')
            )
            self.stdout.write('Ingredient импортированы')
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'[CSV] Файл не найден: {path}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[CSV] Ошибка: {e}')
            )
