import json
import csv

from recipes.models import Ingredient


def load_from_json(filepath):
    print(f'Читаем JSON: {filepath}')
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for item in data:
        name = item.get('name')
        unit = item.get('measurement_unit')

        if name and unit:
            obj, created = Ingredient.objects.get_or_create(
                name=name,
                measurement_unit=unit
            )
            if created:
                count += 1
    print(f'Из JSON добавлено/обновлено: {count}')


def load_from_csv_no_header(filepath):
    """
    Загружает из CSV БЕЗ заголовков.
    Формат ожидается: название,единица (например: абрикосы,г)
    """

    try:
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
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
        print(f"[CSV] Успешно обработано: {count} записей.")
    except FileNotFoundError:
        print(f"[CSV] Файл не найден: {filepath}")
    except Exception as e:
        print(f"[CSV] Ошибка: {e}")


if __name__ == '__main__':
    json_path = 'data/ingredients.json'
    csv_path = 'data/ingredients.csv'

    try:
        load_from_json(json_path)
    except FileNotFoundError:
        print(f'Файл {json_path} не найден. Пропускаем JSON.')
    except Exception as e:
        print(f'Ошибка при чтении JSON: {e}')

    try:
        load_from_csv_no_header(csv_path)
    except FileNotFoundError:
        print(f'Файл {csv_path} не найден. Пропускаем CSV.')
    except Exception as e:
        print(f'Ошибка при чтении CSV: {e}')
