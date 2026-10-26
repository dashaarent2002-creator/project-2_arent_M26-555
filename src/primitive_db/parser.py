"""Разбор сложных частей команд: values, where, set."""

from primitive_db.constants import BOOL_FALSE, BOOL_TRUE, QUOTES


def invalid_value_message(value):
    """Текст ошибки о некорректном значении."""
    return f"Некорректное значение: {value}. Попробуйте снова."


def split_by_commas(text):
    """Делит строку по запятым, не трогая запятые внутри кавычек."""
    parts = []
    current = ""
    open_quote = None
    for char in text:
        if open_quote:
            if char == open_quote:
                open_quote = None
            current += char
        elif char in QUOTES:
            open_quote = char
            current += char
        elif char == ",":
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if open_quote:
        raise ValueError(invalid_value_message(text))
    parts.append(current.strip())
    if any(part == "" for part in parts):
        raise ValueError(invalid_value_message(text))
    return parts


def parse_value(token):
    """Превращает текст значения в str, int или bool."""
    token = token.strip()
    if len(token) >= 2 and token[0] in QUOTES and token[0] == token[-1]:
        return token[1:-1]
    if token.lower() == BOOL_TRUE:
        return True
    if token.lower() == BOOL_FALSE:
        return False
    try:
        return int(token)
    except ValueError:
        return token


def parse_condition(text):
    """Превращает строку вида 'age = 28' в словарь {'age': 28}."""
    if "=" not in text:
        raise ValueError(invalid_value_message(text.strip()))
    column, value = text.split("=", 1)
    column = column.strip()
    if not column or not value.strip():
        raise ValueError(invalid_value_message(text.strip()))
    return {column: parse_value(value)}


def parse_where(text):
    """Разбирает условие where в словарь."""
    return parse_condition(text)


def parse_set(text):
    """Разбирает часть set (можно несколько через запятую) в словарь."""
    result = {}
    for part in split_by_commas(text):
        result.update(parse_condition(part))
    return result


def parse_values(text):
    """Разбирает '(значение1, значение2, ...)' в список значений."""
    text = text.strip()
    if not (text.startswith("(") and text.endswith(")")):
        raise ValueError(invalid_value_message(text))
    inner = text[1:-1]
    return [parse_value(token) for token in split_by_commas(inner)]
