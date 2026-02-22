"""PAPA Lang Runtime Type Checker — validates types at runtime."""

from .environment import PapaError, Maybe, Secret, PapaList, PapaMap


# Маппинг имён типов PAPA → проверочные функции
def _check_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _check_float(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _check_text(v):
    return isinstance(v, str)


def _check_bool(v):
    return isinstance(v, bool)


def _check_list(v):
    return isinstance(v, (PapaList, list))


def _check_map(v):
    return isinstance(v, (PapaMap, dict))


def _check_maybe(v):
    return isinstance(v, Maybe)


def _check_secret(v):
    return isinstance(v, Secret)


def _check_none(v):
    return isinstance(v, Maybe) and not v.exists


PAPA_TYPE_CHECKS = {
    "int": _check_int,
    "float": _check_float,
    "text": _check_text,
    "bool": _check_bool,
    "list": _check_list,
    "map": _check_map,
    "maybe": _check_maybe,
    "secret": _check_secret,
    "any": lambda v: True,
    "none": _check_none,
}


def get_papa_type_name(value) -> str:
    """Определить PAPA-тип значения."""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "text"
    if isinstance(value, Secret):
        return "secret"
    if isinstance(value, Maybe):
        return "maybe"
    if isinstance(value, PapaList):
        return "list"
    if isinstance(value, PapaMap):
        return "map"
    return type(value).__name__


def check_type(value, expected_type: str, context: str, line: int) -> None:
    """
    Проверить что value соответствует expected_type.

    Args:
        value: проверяемое значение
        expected_type: строка типа из аннотации ("int", "text", "maybe", etc.)
        context: контекст для сообщения об ошибке ("параметр 'n' функции 'double'")
        line: номер строки

    Raises:
        PapaError если тип не совпадает
    """
    if expected_type is None:
        return

    # maybe<T> или T? — принимает значение ИЛИ none/Maybe.none()
    is_optional = expected_type.endswith("?")
    base_type = expected_type.rstrip("?")

    if is_optional:
        # Для optional: none/Maybe.none() — OK, иначе проверяем base_type
        if isinstance(value, Maybe):
            if not value.exists:
                return  # none для optional — OK
            value = value.value  # unwrap для проверки внутреннего типа
        elif value is None:
            return  # Python None → OK для optional

    # Проверка по таблице
    checker = PAPA_TYPE_CHECKS.get(base_type)
    if checker is None:
        return  # Неизвестный тип (пользовательский type/model) — пропускаем

    if not checker(value):
        actual = get_papa_type_name(value)
        raise PapaError(
            f"Ошибка типа: {context} ожидает {expected_type}, получено {actual}",
            line=line,
        )


def check_return_type(value, expected_type: str, func_name: str, line: int) -> None:
    """Проверить тип возвращаемого значения."""
    if expected_type is None:
        return
    check_type(
        value,
        expected_type,
        f"возвращаемое значение функции '{func_name}'",
        line,
    )
