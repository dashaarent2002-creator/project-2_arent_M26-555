"""Основная логика: управление таблицами и CRUD-операции."""

from primitive_db.constants import COLUMN_SEPARATOR, ID_COLUMN, ID_TYPE, VALID_TYPES
from primitive_db.decorators import confirm_action, handle_db_errors, log_time
from primitive_db.parser import invalid_value_message
from primitive_db.utils import delete_table_data, load_table_data

TYPE_CHECKS = {
    "int": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "str": lambda value: isinstance(value, str),
    "bool": lambda value: isinstance(value, bool),
}


def format_columns(schema):
    """Возвращает строку вида 'ID:int, name:str'."""
    return ", ".join(f"{name}:{col_type}" for name, col_type in schema.items())


def get_schema(metadata, table_name):
    """Возвращает схему таблицы или выбрасывает ошибку, если таблицы нет."""
    if table_name not in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" не существует.')
    return metadata[table_name]


def is_valid_value(value, column_type):
    """Проверяет, что значение подходит под тип столбца."""
    return TYPE_CHECKS[column_type](value)


def validate_clause(schema, clause):
    """Проверяет, что столбцы условия существуют, а значения нужного типа."""
    for column, value in clause.items():
        if column not in schema:
            raise KeyError(column)
        if not is_valid_value(value, schema[column]):
            raise ValueError(invalid_value_message(value))


def matches(record, where_clause):
    """Проверяет, подходит ли запись под условие where."""
    for column, value in where_clause.items():
        record_value = record.get(column)
        if type(record_value) is not type(value) or record_value != value:
            return False
    return True


def find_ids(table_data, where_clause):
    """Возвращает ID записей, подходящих под условие."""
    return [record[ID_COLUMN] for record in table_data if matches(record, where_clause)]


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Создает таблицу: добавляет ID:int и проверяет типы столбцов."""
    if table_name in metadata:
        raise ValueError(f'Ошибка: Таблица "{table_name}" уже существует.')
    if not columns:
        raise ValueError(invalid_value_message(table_name))

    schema = {ID_COLUMN: ID_TYPE}
    for column in columns:
        if column.count(COLUMN_SEPARATOR) != 1:
            raise ValueError(invalid_value_message(column))
        name, column_type = column.split(COLUMN_SEPARATOR)
        if not name or column_type not in VALID_TYPES or name in schema:
            raise ValueError(invalid_value_message(column))
        schema[name] = column_type

    metadata[table_name] = schema
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет таблицу из метаданных и ее файл с данными."""
    get_schema(metadata, table_name)
    del metadata[table_name]
    delete_table_data(table_name)
    return metadata


def list_tables(metadata):
    """Возвращает список имен всех таблиц."""
    return list(metadata)


@handle_db_errors
def table_info(metadata, table_name):
    """Возвращает схему таблицы и количество записей в ней."""
    schema = get_schema(metadata, table_name)
    return schema, len(load_table_data(table_name))


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавляет запись в таблицу и возвращает обновленные данные."""
    schema = get_schema(metadata, table_name)
    columns = [name for name in schema if name != ID_COLUMN]
    if len(values) != len(columns):
        raise ValueError(
            invalid_value_message(
                f"передано значений {len(values)}, нужно {len(columns)}"
            )
        )
    for column, value in zip(columns, values):
        if not is_valid_value(value, schema[column]):
            raise ValueError(invalid_value_message(value))

    table_data = load_table_data(table_name)
    new_id = max((record[ID_COLUMN] for record in table_data), default=0) + 1
    record = {ID_COLUMN: new_id}
    record.update(zip(columns, values))
    table_data.append(record)
    return table_data


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Возвращает все записи или только подходящие под условие."""
    if not where_clause:
        return list(table_data)
    return [record for record in table_data if matches(record, where_clause)]


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Обновляет поля в записях, подходящих под условие."""
    if ID_COLUMN in set_clause:
        raise ValueError(invalid_value_message(ID_COLUMN))
    for record in table_data:
        if matches(record, where_clause):
            record.update(set_clause)
    return table_data


@handle_db_errors
@confirm_action("удаление записи")
def delete(table_data, where_clause):
    """Удаляет записи, подходящие под условие."""
    return [record for record in table_data if not matches(record, where_clause)]
