"""Запуск, главный цикл и разбор команд пользователя."""

import shlex

import prompt
from prettytable import PrettyTable

from primitive_db.constants import (
    KEYWORD_FROM,
    KEYWORD_INTO,
    KEYWORD_SET,
    KEYWORD_VALUES,
    KEYWORD_WHERE,
    META_FILE,
    PROMPT_TEXT,
)
from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    find_ids,
    format_columns,
    get_schema,
    insert,
    list_tables,
    select,
    table_info,
    update,
    validate_clause,
)
from primitive_db.decorators import create_cacher, handle_db_errors
from primitive_db.parser import (
    invalid_value_message,
    parse_set,
    parse_values,
    parse_where,
)
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)

cache_result = create_cacher()


def print_help():
    """Печатает справку по командам."""
    print("\n***Процесс работы с таблицей***")
    print("Функции:")
    print("<command> create_table <имя_таблицы> <столбец1:тип> .. - создать таблицу")
    print("<command> list_tables - показать список всех таблиц")
    print("<command> drop_table <имя_таблицы> - удалить таблицу")

    print("\n***Операции с данными***")
    print("Функции:")
    print(
        "<command> insert into <имя_таблицы> values "
        "(<значение1>, <значение2>, ...) - создать запись."
    )
    print(
        "<command> select from <имя_таблицы> where <столбец> = <значение> "
        "- прочитать записи по условию."
    )
    print("<command> select from <имя_таблицы> - прочитать все записи.")
    print(
        "<command> update <имя_таблицы> set <столбец1> = <новое_значение1> "
        "where <столбец_условия> = <значение_условия> - обновить запись."
    )
    print(
        "<command> delete from <имя_таблицы> where <столбец> = <значение> "
        "- удалить запись."
    )
    print("<command> info <имя_таблицы> - вывести информацию о таблице.")

    print("\nОбщие команды:")
    print("<command> exit - выход из программы")
    print("<command> help - справочная информация\n")


def split_where(text):
    """Делит строку на часть до where и само условие."""
    index = text.find(KEYWORD_WHERE)
    if index == -1:
        return text, None
    return text[:index], text[index + len(KEYWORD_WHERE):]


def text_after(text, word, start=0):
    """Возвращает часть строки после слова word (поиск начиная с start)."""
    index = text.find(word, start)
    if index == -1:
        raise ValueError(invalid_value_message(text))
    return text[index + len(word):]


def print_records(schema, records):
    """Выводит записи в виде таблицы PrettyTable."""
    table = PrettyTable(list(schema))
    for record in records:
        table.add_row([record.get(column) for column in schema])
    print(table)


def handle_create_table(metadata, args):
    """Команда create_table."""
    if len(args) < 3:
        raise ValueError(invalid_value_message(" ".join(args[1:]) or "пусто"))
    table_name = args[1]
    result = create_table(metadata, table_name, args[2:])
    if result is None:
        return
    save_metadata(META_FILE, result)
    columns = format_columns(result[table_name])
    print(f'Таблица "{table_name}" успешно создана со столбцами: {columns}')


def handle_drop_table(metadata, args):
    """Команда drop_table."""
    if len(args) != 2:
        raise ValueError(invalid_value_message(" ".join(args[1:]) or "пусто"))
    get_schema(metadata, args[1])
    result = drop_table(metadata, args[1])
    if result is None:
        return
    save_metadata(META_FILE, result)
    print(f'Таблица "{args[1]}" успешно удалена.')


def handle_list_tables(metadata):
    """Команда list_tables."""
    tables = list_tables(metadata)
    if not tables:
        print("Таблиц пока нет.")
    for table_name in tables:
        print(f"- {table_name}")


def handle_insert(metadata, args, user_input):
    """Команда insert into <таблица> values (...)."""
    if len(args) < 5 or args[1] != KEYWORD_INTO or args[3] != KEYWORD_VALUES:
        raise ValueError(invalid_value_message(user_input))
    table_name = args[2]
    table_start = user_input.find(table_name) + len(table_name)
    values = parse_values(text_after(user_input, KEYWORD_VALUES, table_start))
    table_data = insert(metadata, table_name, values)
    if table_data is None:
        return
    save_table_data(table_name, table_data)
    new_id = table_data[-1]["ID"]
    print(f'Запись с ID={new_id} успешно добавлена в таблицу "{table_name}".')


def handle_select(metadata, args, user_input):
    """Команда select from <таблица> [where ...]."""
    if len(args) < 3 or args[1] != KEYWORD_FROM:
        raise ValueError(invalid_value_message(user_input))
    table_name = args[2]
    schema = get_schema(metadata, table_name)
    _, where_text = split_where(user_input)
    where_clause = parse_where(where_text) if where_text else None
    if where_clause:
        validate_clause(schema, where_clause)

    table_data = load_table_data(table_name)
    cache_key = f"{table_name}|{where_clause}|{table_data}"
    records = cache_result(cache_key, lambda: select(table_data, where_clause))
    if records is None:
        return
    if not records:
        print("Записи не найдены.")
        return
    print_records(schema, records)


def handle_update(metadata, args, user_input):
    """Команда update <таблица> set ... where ...."""
    if len(args) < 4 or args[2] != KEYWORD_SET:
        raise ValueError(invalid_value_message(user_input))
    table_name = args[1]
    schema = get_schema(metadata, table_name)
    rest = text_after(user_input, f" {KEYWORD_SET} ")
    set_text, where_text = split_where(rest)
    if not where_text:
        raise ValueError(invalid_value_message(user_input))
    set_clause = parse_set(set_text)
    where_clause = parse_where(where_text)
    validate_clause(schema, set_clause)
    validate_clause(schema, where_clause)

    table_data = load_table_data(table_name)
    ids = find_ids(table_data, where_clause)
    if not ids:
        print("Записи по условию не найдены.")
        return
    result = update(table_data, set_clause, where_clause)
    if result is None:
        return
    save_table_data(table_name, result)
    for record_id in ids:
        print(f'Запись с ID={record_id} в таблице "{table_name}" успешно обновлена.')


def handle_delete(metadata, args, user_input):
    """Команда delete from <таблица> where ...."""
    if len(args) < 4 or args[1] != KEYWORD_FROM:
        raise ValueError(invalid_value_message(user_input))
    table_name = args[2]
    schema = get_schema(metadata, table_name)
    _, where_text = split_where(user_input)
    if not where_text:
        raise ValueError(invalid_value_message(user_input))
    where_clause = parse_where(where_text)
    validate_clause(schema, where_clause)

    table_data = load_table_data(table_name)
    ids = find_ids(table_data, where_clause)
    if not ids:
        print("Записи по условию не найдены.")
        return
    result = delete(table_data, where_clause)
    if result is None:
        return
    save_table_data(table_name, result)
    for record_id in ids:
        print(f'Запись с ID={record_id} успешно удалена из таблицы "{table_name}".')


def handle_info(metadata, args):
    """Команда info <таблица>."""
    if len(args) != 2:
        raise ValueError(invalid_value_message(" ".join(args[1:]) or "пусто"))
    result = table_info(metadata, args[1])
    if result is None:
        return
    schema, count = result
    print(f"Таблица: {args[1]}")
    print(f"Столбцы: {format_columns(schema)}")
    print(f"Количество записей: {count}")


@handle_db_errors
def execute_command(metadata, args, user_input):
    """Вызывает нужную функцию по имени команды."""
    match args[0]:
        case "help":
            print_help()
        case "create_table":
            handle_create_table(metadata, args)
        case "drop_table":
            handle_drop_table(metadata, args)
        case "list_tables":
            handle_list_tables(metadata)
        case "insert":
            handle_insert(metadata, args, user_input)
        case "select":
            handle_select(metadata, args, user_input)
        case "update":
            handle_update(metadata, args, user_input)
        case "delete":
            handle_delete(metadata, args, user_input)
        case "info":
            handle_info(metadata, args)
        case _:
            print(f"Функции {args[0]} нет. Попробуйте снова.")


def run():
    """Главный цикл программы."""
    print("\n***База данных***")
    print_help()
    while True:
        metadata = load_metadata(META_FILE)
        try:
            user_input = prompt.string(PROMPT_TEXT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        try:
            args = shlex.split(user_input)
        except ValueError:
            print(invalid_value_message(user_input))
            continue
        if args[0] == "exit":
            print("Выход из программы.")
            break
        execute_command(metadata, args, user_input)
