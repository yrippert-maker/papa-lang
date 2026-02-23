"""
PAPA Lang Evaluator — expression evaluation (EvaluatorMixin).
"""

import threading
from typing import Any

from .ast_nodes import (
    IntLiteral, FloatLiteral, TextLiteral, BoolLiteral, NoneLiteral,
    Identifier, BinaryOp, UnaryOp, FunctionCall, MemberAccess,
    OptionalChain, NullCoalesce, ListLiteral, MapLiteral, RangeLiteral, IndexAccess,
    FunctionDef,
)
from .environment import (
    Environment, Maybe, PapaList, PapaMap, PapaError,
    ReturnSignal, FailSignal,
)
from .type_checker import check_type, check_return_type


class EvaluatorMixin:
    """Mixin providing eval_* methods for Interpreter."""

    def eval_IntLiteral(self, node: IntLiteral, env: Environment) -> int:
        return node.value

    def eval_FloatLiteral(self, node: FloatLiteral, env: Environment) -> float:
        return node.value

    def eval_TextLiteral(self, node: TextLiteral, env: Environment) -> str:
        text = node.value
        result = []
        i = 0
        while i < len(text):
            if text[i] == '{' and i + 1 < len(text):
                depth = 1
                j = i + 1
                while j < len(text) and depth > 0:
                    if text[j] == '{': depth += 1
                    elif text[j] == '}': depth -= 1
                    j += 1
                expr_str = text[i+1:j-1]
                try:
                    from .lexer import lex as lex_fn
                    from .parser import parse as parse_fn
                    tokens = lex_fn(expr_str)
                    ast = parse_fn(tokens, expr_str)
                    if ast.statements:
                        val = self.evaluate(ast.statements[0], env)
                        result.append(str(val))
                    else:
                        result.append(expr_str)
                except Exception:
                    try:
                        val = env.get(expr_str.strip(), node.line)
                        result.append(str(val))
                    except Exception:
                        result.append('{' + expr_str + '}')
                i = j
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)

    def eval_BoolLiteral(self, node: BoolLiteral, env: Environment) -> bool:
        return node.value

    def eval_NoneLiteral(self, node: NoneLiteral, env: Environment) -> Maybe:
        return Maybe.none()

    def eval_Identifier(self, node: Identifier, env: Environment) -> Any:
        name = node.name
        if name in self.builtins:
            return ('builtin', name)
        if name == 'true':
            return True
        if name == 'false':
            return False
        try:
            return env.get_function(name, node.line)
        except PapaError:
            pass
        return env.get(name, node.line)

    def _div_zero_error(self, node):
        raise PapaError("Деление на ноль", line=node.line,
                       hint="Проверьте делитель перед делением")

    def eval_BinaryOp(self, node: BinaryOp, env: Environment) -> Any:
        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        ops = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b if b != 0 else self._div_zero_error(node),
            '%': lambda a, b: a % b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
            'is': lambda a, b: a == b or (isinstance(a, type) and isinstance(b, a)),
            'and': lambda a, b: a and b,
            'or': lambda a, b: a or b,
        }

        if node.op in ops:
            try:
                return ops[node.op](left, right)
            except TypeError:
                lt, rt = type(left).__name__, type(right).__name__
                hint = f"Проверьте типы: слева {repr(left)[:30]}, справа {repr(right)[:30]}"
                if node.op == "+" and ("str" in lt or "str" in rt or "text" in lt or "text" in rt):
                    hint = "Преобразуйте: str(42) + \" штук\" или \"{42} штук\""
                raise PapaError(
                    f"Нельзя применить '{node.op}' к {lt} и {rt}",
                    line=node.line,
                    hint=hint
                )

        raise PapaError(f"Неизвестный оператор: {node.op}", line=node.line)

    def eval_UnaryOp(self, node: UnaryOp, env: Environment) -> Any:
        val = self.evaluate(node.operand, env)
        if node.op == '-':
            return -val
        if node.op == 'not':
            return not val
        raise PapaError(f"Неизвестный унарный оператор: {node.op}", line=node.line)

    def eval_FunctionCall(self, node: FunctionCall, env: Environment) -> Any:
        if isinstance(node.name, MemberAccess):
            obj = self.evaluate(node.name.object, env)
            method = node.name.member
            if hasattr(obj, '_is_papa_model') and obj._is_papa_model and method == 'where':
                args = []
            else:
                args = [self.evaluate(a, env) for a in node.args]
            named_args = {k: self.evaluate(v, env) for k, v in (node.named_args or {}).items()}
            return self._call_method(obj, method, args, node.line, named_args, node)

        args = [self.evaluate(a, env) for a in node.args]
        named_args = {k: self.evaluate(v, env) for k, v in (node.named_args or {}).items()}

        func = self.evaluate(node.name, env)

        if isinstance(func, tuple) and func[0] == 'builtin':
            return self.builtins[func[1]](args)

        if callable(func):
            return func(args)

        if isinstance(func, FunctionDef):
            if func.is_async:
                def run_async():
                    self._call_function(func, args, env)

                t = threading.Thread(target=run_async, daemon=True)
                t.start()
                self.tasks.append(t)
                return None
            return self._call_function(func, args, env, named_args)

        raise PapaError(
            f"'{node.name}' не является функцией",
            line=node.line,
            hint="Проверьте определение функции"
        )

    def _call_function(self, func: FunctionDef, args: list, env: Environment, named_args: dict = None) -> Any:
        named_args = named_args or {}
        func_env = Environment(parent=env)

        for pname, value in named_args.items():
            func_env.set(pname, value)

        for i, (pname, ptype, pdefault) in enumerate(func.params):
            if pname in named_args:
                continue
            if i < len(args):
                value = args[i]
            elif pdefault is not None:
                value = self.evaluate(pdefault, env)
            else:
                raise PapaError(
                    f"Функция '{func.name}' ожидает аргумент '{pname}'",
                    line=func.line,
                    hint=f"Вызов: {func.name}({', '.join(p[0] for p in func.params)})"
                )
            # Runtime type checking
            if ptype:
                check_type(
                    value,
                    ptype,
                    f"параметр '{pname}' функции '{func.name}'",
                    func.line,
                )
            func_env.set(pname, value)

        result = None
        try:
            for stmt in func.body:
                result = self.execute(stmt, func_env)
        except ReturnSignal as ret:
            result = ret.value
        except FailSignal:
            if func.can_fail:
                raise
            raise

        # Return type checking
        if func.return_type and result is not None:
            check_return_type(result, func.return_type, func.name, func.line)

        return result

    def _call_method(self, obj, method: str, args: list, line: int, named_args: dict = None, call_node=None) -> Any:
        named_args = named_args or {}
        if isinstance(obj, str):
            str_methods = {
                'length': lambda: len(obj),
                'upper': lambda: obj.upper(),
                'lower': lambda: obj.lower(),
                'trim': lambda: obj.strip(),
                'contains': lambda: args[0] in obj if args else False,
                'starts_with': lambda: obj.startswith(args[0]) if args else False,
                'ends_with': lambda: obj.endswith(args[0]) if args else False,
                'repeat': lambda: obj * int(args[0]) if args else obj,
                'chars': lambda: PapaList(list(obj)),
                'index_of': lambda: obj.find(args[0]) if args else -1,
                'split': lambda: PapaList(obj.split(args[0]) if args else obj.split()),
                'replace': lambda: obj.replace(args[0], args[1]) if len(args) >= 2 else obj,
            }
            if method in str_methods:
                return str_methods[method]()

        if isinstance(obj, PapaList):
            list_methods = {
                'add': lambda: obj.add(args[0]) if args else obj,
                'at': lambda: obj.at(int(args[0])) if args else Maybe.none(),
                'contains': lambda: args[0] in obj._items if args else False,
                'join': lambda: args[0].join(str(x) for x in obj._items) if args else ', '.join(str(x) for x in obj._items),
                'reverse': lambda: PapaList(list(reversed(obj._items))),
                'sort': lambda: PapaList(sorted(obj._items)),
            }
            if method in list_methods:
                return list_methods[method]()

        if isinstance(obj, Maybe):
            if method == 'value':
                return obj.value
            if method == 'exists':
                return obj.exists

        if isinstance(obj, PapaMap):
            if method == 'get':
                return obj.get(args[0]) if args else Maybe.none()
            if method == 'set':
                return obj.set(args[0], args[1]) if len(args) >= 2 else obj
            # AI agent .run(input) — callable attribute
            if hasattr(obj, method) and callable(getattr(obj, method)):
                return getattr(obj, method)(args)

        if hasattr(obj, '_is_papa_model') and obj._is_papa_model:
            if method == 'create':
                return obj.create(**named_args)
            if method == 'all':
                return obj.all()
            if method == 'count':
                return obj.count()
            if method == 'find':
                return obj.find(**named_args)
            if method == 'where':
                if call_node and call_node.args:
                    return obj.where(call_node.args[0])
                raise PapaError("where() требует условие", line=line, hint="User.where(age >= 18)")
            if method == 'delete':
                if args:
                    obj.delete(args[0])
                    return None
                raise PapaError("delete() требует запись", line=line)

        if isinstance(obj, dict):
            if method in obj:
                return obj[method]

        raise PapaError(
            f"Метод '{method}' не найден для типа {type(obj).__name__}",
            line=line,
            hint="Доступные методы зависят от типа объекта"
        )

    def eval_MemberAccess(self, node: MemberAccess, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)

        if isinstance(obj, dict):
            if node.member in obj:
                return obj[node.member]
            return Maybe.none()

        if isinstance(obj, PapaMap):
            # Python attributes (e.g. agent.run) take precedence
            if hasattr(obj, node.member):
                return getattr(obj, node.member)
            return obj.get(node.member)

        if isinstance(obj, PapaList):
            props = {'count': obj.count, 'first': obj.first, 'last': obj.last, 'empty': obj.empty}
            if node.member in props:
                return props[node.member]

        if isinstance(obj, Maybe):
            if node.member == 'exists':
                return obj.exists
            if node.member == 'value':
                return obj.value

        if isinstance(obj, str):
            if node.member == 'length':
                return len(obj)
            if node.member == 'empty':
                return len(obj) == 0

        if hasattr(obj, node.member):
            return getattr(obj, node.member)

        raise PapaError(
            f"Свойство '{node.member}' не найдено",
            line=node.line,
            hint=f"Объект типа {type(obj).__name__} не имеет свойства '{node.member}'"
        )

    def eval_OptionalChain(self, node: OptionalChain, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)
        if isinstance(obj, Maybe):
            if not obj.exists:
                return Maybe.none()
            obj = obj.value
        if obj is None:
            return Maybe.none()
        try:
            result = self.eval_MemberAccess(
                MemberAccess(object=node.object, member=node.member, line=node.line),
                env
            )
            return Maybe.some(result)
        except PapaError:
            return Maybe.none()

    def eval_NullCoalesce(self, node: NullCoalesce, env: Environment) -> Any:
        left = self.evaluate(node.expr, env)
        if isinstance(left, Maybe):
            if left.exists:
                return left.value
            return self.evaluate(node.default, env)
        if left is None:
            return self.evaluate(node.default, env)
        return left

    def eval_ListLiteral(self, node: ListLiteral, env: Environment) -> PapaList:
        elements = [self.evaluate(e, env) for e in node.elements]
        return PapaList(elements)

    def eval_MapLiteral(self, node: MapLiteral, env: Environment) -> PapaMap:
        result_pairs = []
        for k, v in node.pairs:
            if isinstance(k, Identifier):
                key_val = k.name
            else:
                key_val = self.evaluate(k, env)
            result_pairs.append((key_val, self.evaluate(v, env)))
        return PapaMap(result_pairs)

    def eval_RangeLiteral(self, node: RangeLiteral, env: Environment) -> PapaList:
        start = self.evaluate(node.start, env)
        end = self.evaluate(node.end, env)
        return PapaList(list(range(int(start), int(end) + 1)))

    def eval_IndexAccess(self, node: IndexAccess, env: Environment) -> Any:
        obj = self.evaluate(node.object, env)
        index = self.evaluate(node.index, env)
        if isinstance(obj, PapaList):
            return obj.at(int(index))
        if isinstance(obj, PapaMap):
            return obj.get(index)
        if isinstance(obj, list):
            idx = int(index)
            if 0 <= idx < len(obj):
                return Maybe.some(obj[idx])
            return Maybe.none()
        if isinstance(obj, str):
            idx = int(index)
            if 0 <= idx < len(obj):
                return obj[idx]
            return Maybe.none()
        raise PapaError(f"Тип {type(obj).__name__} не поддерживает индексацию", line=node.line)


__all__ = ['EvaluatorMixin']
