"""
PAPA Lang Environment — Runtime types, signals, scope management.
"""

from typing import Any, Dict, TYPE_CHECKING

from .ast_nodes import FunctionDef, TypeDef, RouteDef, TestDef, ServeDef

if TYPE_CHECKING:
    from .interpreter import Interpreter


def _levenshtein(a: str, b: str) -> int:
    """Расстояние Левенштейна."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    n, m = len(a), len(b)
    dp = [list(range(m + 1))]
    for i in range(1, n + 1):
        row = [i]
        for j in range(1, m + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            row.append(min(dp[i - 1][j] + 1, row[j - 1] + 1, dp[i - 1][j - 1] + c))
        dp.append(row)
    return dp[n][m]


def _find_similar_names(name: str, candidates: list, max_dist: int = 2) -> list:
    """Найти похожие имена (Левенштейн ≤ max_dist)."""
    result = []
    for c in candidates:
        if _levenshtein(name, c) <= max_dist:
            result.append(c)
    return sorted(result)[:3]


class PapaError(Exception):
    """Runtime error with friendly formatting."""
    def __init__(self, message: str, line: int = 0, hint: str = ""):
        self.line = line
        self.hint = hint
        formatted = f"\n── ОШИБКА в строке {line} ──\n\n  {message}\n"
        if hint:
            formatted += f"\n  💡 Подсказка: {hint}\n"
        super().__init__(formatted)


class BreakSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class FailSignal(Exception):
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"\n── FAIL в строке {line} ──\n\n  {message}\n")


# ── Built-in Types ──

class Maybe:
    """PAPA Lang's maybe type — replaces null/undefined."""
    def __init__(self, value=None, has_value=False):
        self._value = value
        self._has = has_value

    @staticmethod
    def some(value):
        return Maybe(value, True)

    @staticmethod
    def none():
        return Maybe(None, False)

    @property
    def exists(self):
        return self._has

    @property
    def value(self):
        if not self._has:
            raise PapaError("Попытка получить значение из пустого maybe",
                          hint="Используйте 'match' или '??' для безопасного доступа")
        return self._value

    def __repr__(self):
        if self._has:
            return f"some({self._value!r})"
        return "none"

    def __bool__(self):
        return self._has

    def __eq__(self, other):
        if isinstance(other, Maybe):
            if not self._has and not other._has:
                return True
            if self._has and other._has:
                return self._value == other._value
            return False
        return False


class Secret:
    """PAPA Lang's secret type — never leaks to logs."""
    def __init__(self, value: str):
        self._value = value

    @property
    def raw(self):
        return self._value

    def __repr__(self):
        return "***REDACTED***"

    def __str__(self):
        return "***REDACTED***"

    def __eq__(self, other):
        if isinstance(other, Secret):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False


class PapaList:
    """PAPA Lang's list — safe access, no index out of bounds."""
    def __init__(self, elements=None):
        self._items = list(elements) if elements else []

    @property
    def count(self):
        return len(self._items)

    @property
    def first(self):
        if self._items:
            return Maybe.some(self._items[0])
        return Maybe.none()

    @property
    def last(self):
        if self._items:
            return Maybe.some(self._items[-1])
        return Maybe.none()

    def at(self, index):
        if 0 <= index < len(self._items):
            return Maybe.some(self._items[index])
        return Maybe.none()

    def add(self, item):
        new_list = PapaList(self._items)
        new_list._items.append(item)
        return new_list

    def where(self, pred):
        return PapaList([x for x in self._items if pred(x)])

    @property
    def empty(self):
        return len(self._items) == 0

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        return f"[{', '.join(repr(x) for x in self._items)}]"

    def __getitem__(self, index):
        return self.at(index)


class PapaModelInstance:
    """Instance of a PAPA model — dict-like with .field access."""
    def __init__(self, data: dict, model: 'PapaModel'):
        self._data = dict(data)
        self._model = model

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        raise PapaError(f"Поле '{name}' не найдено в {self._model.name}")

    def __repr__(self):
        return f"{{{', '.join(f'{k}: {v!r}' for k, v in self._data.items())}}}"


class PapaModel:
    """PAPA Lang's model — in-memory ORM."""
    _is_papa_model = True

    def __init__(self, name: str, fields: list, interpreter: 'Interpreter'):
        self.name = name
        self.fields = fields  # [(name, type, modifiers), ...]
        self._store = []
        self._interp = interpreter

    def create(self, **kwargs) -> PapaModelInstance:
        data = {}
        for fname, ftype, mods in self.fields:
            if fname in kwargs:
                data[fname] = kwargs[fname]
            else:
                raise PapaError(
                    f"Поле '{fname}' обязательно для {self.name}.create()",
                    hint=f"Укажите: {fname}: значение"
                )
        for k in kwargs:
            if k not in [f[0] for f in self.fields]:
                raise PapaError(f"Неизвестное поле '{k}' в модели {self.name}")
        for fname, ftype, mods in self.fields:
            if 'unique' in mods:
                for rec in self._store:
                    if rec._data.get(fname) == data[fname]:
                        raise PapaError(
                            f"Значение '{data[fname]}' уже существует для уникального поля '{fname}'"
                        )
        inst = PapaModelInstance(data, self)
        self._store.append(inst)
        return inst

    def all(self) -> PapaList:
        return PapaList(list(self._store))

    def find(self, **kwargs) -> Maybe:
        for rec in self._store:
            if all(rec._data.get(k) == v for k, v in kwargs.items()):
                return Maybe.some(rec)
        return Maybe.none()

    def where(self, condition) -> PapaList:
        result = []
        for rec in self._store:
            try:
                env = Environment()
                for k, v in rec._data.items():
                    env.set(k, v)
                if self._interp.evaluate(condition, env):
                    result.append(rec)
            except Exception:
                pass
        return PapaList(result)

    def count(self) -> int:
        return len(self._store)

    def delete(self, rec: PapaModelInstance) -> None:
        if rec in self._store:
            self._store.remove(rec)


class PapaMap:
    """PAPA Lang's map — safe access."""
    def __init__(self, pairs=None):
        self._data = dict(pairs) if pairs else {}

    def get(self, key):
        if key in self._data:
            return Maybe.some(self._data[key])
        return Maybe.none()

    def set(self, key, value):
        new_map = PapaMap(self._data.items())
        new_map._data[key] = value
        return new_map

    @property
    def keys(self):
        return PapaList(self._data.keys())

    @property
    def count(self):
        return len(self._data)

    def __repr__(self):
        pairs = ', '.join(f'{k!r} -> {v!r}' for k, v in self._data.items())
        return '{' + pairs + '}'


# ── Environment ──

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars: Dict[str, Any] = {}
        self.mutables: set = set()
        self.functions: Dict[str, FunctionDef] = {}
        self.types: Dict[str, TypeDef] = {}

    def _all_names(self) -> set:
        names = set(self.vars) | set(self.functions)
        if self.parent:
            names |= self.parent._all_names()
        return names

    def get(self, name: str, line: int = 0) -> Any:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name, line)
        similar = _find_similar_names(name, list(self._all_names()))
        hint = f"Определите переменную: {name} = значение"
        if similar:
            hint += f"\n  💡 Вы имели в виду: {', '.join(similar)}?"
        raise PapaError(
            f"Переменная '{name}' не определена",
            line=line,
            hint=hint
        )

    def set(self, name: str, value: Any, mutable: bool = False, line: int = 0):
        if name in self.vars and name not in self.mutables:
            raise PapaError(
                f"Переменная '{name}' иммутабельная — нельзя изменить",
                line=line,
                hint=f"Используйте 'mut {name} = ...' для мутабельной переменной"
            )
        self.vars[name] = value
        if mutable:
            self.mutables.add(name)

    def reassign(self, name: str, value: Any, line: int = 0):
        if name in self.vars:
            if name not in self.mutables:
                raise PapaError(
                    f"Переменная '{name}' иммутабельная — нельзя изменить",
                    line=line,
                    hint=f"Используйте 'mut {name} = ...' для мутабельной переменной"
                )
            self.vars[name] = value
            return
        if self.parent:
            self.parent.reassign(name, value, line)
            return
        raise PapaError(f"Переменная '{name}' не определена", line=line)

    def define_function(self, name: str, func: FunctionDef):
        self.functions[name] = func

    def get_function(self, name: str, line: int = 0) -> FunctionDef:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_function(name, line)
        similar = _find_similar_names(name, list(self._all_names()))
        hint = f"Определите функцию: {name}(...) -> ..."
        if similar:
            hint += f"\n  💡 Вы имели в виду: {', '.join(similar)}?"
        raise PapaError(f"Функция '{name}' не определена", line=line, hint=hint)


__all__ = [
    '_levenshtein', '_find_similar_names',
    'PapaError', 'BreakSignal', 'ReturnSignal', 'FailSignal',
    'Maybe', 'Secret', 'PapaList', 'PapaModelInstance', 'PapaModel', 'PapaMap',
    'Environment',
]
