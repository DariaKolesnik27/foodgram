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
            count = 0
            with open(path, encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        name = row[0].strip()
                        unit = row[1].strip()

                        if name and unit:
                            obj, created = Ingredient.objects.get_or_create(
                                name=name,
                                measurement_unit=unit
                            )
                            if created:
                                count += 1
            print(f'Успешно обработано: {count} записей.')
            self.stdout.write('Ingredient импортированы')
        except FileNotFoundError:
            print(f'[CSV] Файл не найден: {path}')
        except Exception as e:
            print(f'[CSV] Ошибка: {e}')
