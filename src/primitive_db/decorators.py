"""Декораторы и замыкание для кэширования."""

import time

import prompt

from primitive_db.constants import CONFIRM_YES


def copy_meta(wrapper, func):
    """Переносит имя и описание исходной функции на обертку."""
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def handle_db_errors(func):
    """Перехватывает ошибки базы данных и выводит понятное сообщение."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(error)
        except Exception as error:
            print(f"Произошла непредвиденная ошибка: {error}")
        return None

    return copy_meta(wrapper, func)


def confirm_action(action_name):
    """Фабрика декораторов: спрашивает подтверждение опасного действия."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            question = f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: '
            try:
                answer = prompt.string(question)
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer.strip().lower() != CONFIRM_YES:
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        return copy_meta(wrapper, func)

    return decorator


def log_time(func):
    """Замеряет и выводит время выполнения функции."""

    def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = func(*args, **kwargs)
        elapsed = time.monotonic() - start
        print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд.")
        return result

    return copy_meta(wrapper, func)


def create_cacher():
    """Создает функцию кэширования, хранящую кэш в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        """Возвращает результат из кэша или вычисляет и сохраняет его."""
        if key in cache:
            return cache[key]
        result = value_func()
        cache[key] = result
        return result

    return cache_result
