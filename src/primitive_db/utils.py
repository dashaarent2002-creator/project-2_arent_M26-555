"""Вспомогательные функции для работы с файлами."""

import json
import os

from primitive_db.constants import DATA_DIR, FILE_EXTENSION


def load_metadata(filepath):
    """Загружает метаданные из JSON-файла. Если файла нет, возвращает {}."""
    try:
        with open(filepath, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_metadata(filepath, data):
    """Сохраняет метаданные в JSON-файл."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def get_table_path(table_name):
    """Возвращает путь к файлу с данными таблицы."""
    return os.path.join(DATA_DIR, table_name + FILE_EXTENSION)


def load_table_data(table_name):
    """Загружает записи таблицы. Если файла нет, возвращает пустой список."""
    try:
        with open(get_table_path(table_name), encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_table_data(table_name, data):
    """Сохраняет записи таблицы в файл data/<имя_таблицы>.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(get_table_path(table_name), "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def delete_table_data(table_name):
    """Удаляет файл с данными таблицы, если он существует."""
    path = get_table_path(table_name)
    if os.path.exists(path):
        os.remove(path)
