"""
PAPA Lang Executor — statement execution (ExecutorMixin).
"""

import time
import threading
from typing import Any

from .ast_nodes import (
    Assignment, Reassignment, SayStatement, LogStatement,
    ReturnStatement, FailStatement, IfStatement, MatchStatement,
    ForLoop, LoopStatement, RepeatStatement, WaitStatement, AssertStatement,
    FunctionDef, TypeDef, ModelDef, EnumDef, RouteDef, ServeDef, TestDef, TaskDef, EveryDef,
    Identifier, ImportStatement, FromImportStatement,
)
from .environment import (
    Environment, Maybe, PapaList, PapaMap, PapaModel,
    PapaError, BreakSignal, ReturnSignal, FailSignal,
)
from .type_checker import check_type


class ExecutorMixin:
    """Mixin providing exec_* methods for Interpreter."""

    def exec_Assignment(self, node: Assignment, env: Environment) -> None:
        value = self.evaluate(node.value, env)
        if node.type_annotation:
            check_type(
                value,
                node.type_annotation,
                f"переменная '{node.name}'",
                node.line,
            )
        env.set(node.name, value, mutable=node.mutable, line=node.line)

    def exec_Reassignment(self, node: Reassignment, env: Environment) -> None:
        value = self.evaluate(node.value, env)
        if isinstance(node.target, Identifier):
            env.reassign(node.target.name, value, line=node.line)
        else:
            raise PapaError("Нельзя присвоить значение этому выражению", line=node.line)

    def exec_SayStatement(self, node: SayStatement, env: Environment) -> None:
        value = self.evaluate(node.expr, env)
        text = str(value)
        self.output.append(text)
        print(text)

    def exec_LogStatement(self, node: LogStatement, env: Environment) -> None:
        value = self.evaluate(node.expr, env)
        timestamp = time.strftime("%H:%M:%S")
        level_icons = {'info': 'ℹ️', 'warn': '⚠️', 'error': '❌', 'debug': '🔧', 'fatal': '💀'}
        icon = level_icons.get(node.level, 'ℹ️')
        text = f"[{timestamp}] {icon} {node.level.upper()}: {value}"
        self.output.append(text)
        print(text)

    def exec_ReturnStatement(self, node: ReturnStatement, env: Environment):
        value = self.evaluate(node.value, env) if node.value else None
        raise ReturnSignal(value)

    def exec_FailStatement(self, node: FailStatement, env: Environment):
        message = self.evaluate(node.message, env)
        raise FailSignal(str(message), line=node.line)

    def exec_IfStatement(self, node: IfStatement, env: Environment) -> Any:
        condition = self.evaluate(node.condition, env)
        if isinstance(condition, Maybe):
            condition = condition.exists
        if condition:
            for stmt in node.body:
                self.execute(stmt, env)
        else:
            for elif_cond, elif_body in node.elif_branches:
                cond = self.evaluate(elif_cond, env)
                if isinstance(cond, Maybe):
                    cond = cond.exists
                if cond:
                    for stmt in elif_body:
                        self.execute(stmt, env)
                    return
            for stmt in node.else_body:
                self.execute(stmt, env)

    def _match_pattern(self, value, pattern, env) -> bool:
        if isinstance(pattern, Identifier):
            if pattern.name == 'some' and isinstance(value, Maybe) and value.exists:
                return True
            if pattern.name == 'none' and isinstance(value, Maybe) and not value.exists:
                return True
            if pattern.name == '_':
                return True
            pat_val = self.evaluate(pattern, env)
            return value == pat_val
        pat_val = self.evaluate(pattern, env)
        return value == pat_val

    def exec_MatchStatement(self, node: MatchStatement, env: Environment) -> Any:
        value = self.evaluate(node.expr, env)
        for pattern, body in node.arms:
            if self._match_pattern(value, pattern, env):
                result = None
                for stmt in body:
                    result = self.execute(stmt, env)
                return result
        raise PapaError(
            f"Ни один паттерн не совпал в match для значения: {value!r}",
            line=node.line,
            hint="Добавьте обработку всех возможных вариантов"
        )

    def exec_ForLoop(self, node: ForLoop, env: Environment) -> None:
        iterable = self.evaluate(node.iterable, env)
        if isinstance(iterable, PapaList):
            items = iterable._items
        elif isinstance(iterable, list):
            items = iterable
        elif isinstance(iterable, range):
            items = iterable
        elif isinstance(iterable, str):
            items = list(iterable)
        else:
            raise PapaError(
                f"Нельзя итерировать по типу {type(iterable).__name__}",
                line=node.line,
                hint="Используйте список, диапазон (1..10) или текст"
            )
        env.set(node.var, None, mutable=True)
        index_var = getattr(node, 'index_var', None)
        if index_var:
            env.set(index_var, 0, mutable=True)
        for i, item in enumerate(items):
            if index_var:
                env.vars[index_var] = i
            env.vars[node.var] = item
            try:
                for stmt in node.body:
                    self.execute(stmt, env)
            except BreakSignal:
                break

    def exec_LoopStatement(self, node: LoopStatement, env: Environment) -> None:
        loop_env = Environment(parent=env)
        while True:
            try:
                for stmt in node.body:
                    self.execute(stmt, loop_env)
            except BreakSignal:
                break

    def exec_RepeatStatement(self, node: RepeatStatement, env: Environment) -> None:
        count = self.evaluate(node.count, env)
        completed = False
        for i in range(int(count)):
            try:
                for stmt in node.body:
                    self.execute(stmt, env)
                completed = True
            except BreakSignal:
                completed = True
                break
        if not completed and node.else_body:
            for stmt in node.else_body:
                self.execute(stmt, env)

    def exec_WaitStatement(self, node: WaitStatement, env: Environment) -> None:
        duration = self.evaluate(node.duration, env)
        multipliers = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
        seconds = float(duration) * multipliers.get(node.unit, 1)
        time.sleep(seconds)

    def exec_AssertStatement(self, node: AssertStatement, env: Environment) -> None:
        result = self.evaluate(node.expr, env)
        if isinstance(result, Maybe):
            result = result.exists
        if not result:
            raise PapaError(
                "Утверждение не выполнено",
                line=node.line,
                hint="Проверьте условие в assert"
            )

    def exec_FunctionDef(self, node: FunctionDef, env: Environment) -> None:
        env.define_function(node.name, node)

    def exec_TypeDef(self, node: TypeDef, env: Environment) -> None:
        env.types[node.name] = node

    def exec_ModelDef(self, node: ModelDef, env: Environment) -> None:
        model = PapaModel(node.name, node.fields, self)
        env.set(node.name, model)

    def exec_EnumDef(self, node: EnumDef, env: Environment) -> None:
        enum_map = PapaMap([(v, v) for v in node.variants])
        env.set(node.name, enum_map)

    def exec_ServeDef(self, node: ServeDef, env: Environment) -> None:
        self.serve_config = node
        text = f"🚀 Сервер настроен на порту {node.port}"
        self.output.append(text)
        print(text)

    def exec_RouteDef(self, node: RouteDef, env: Environment) -> None:
        key = f"{node.method} {node.path}"
        self.routes[key] = node
        auth_str = " 🔒" if node.auth_required else ""
        text = f"  📡 {node.method} {node.path}{auth_str}"
        self.output.append(text)
        print(text)

    def exec_TestDef(self, node: TestDef, env: Environment) -> None:
        self.tests.append(node)

    def exec_TaskDef(self, node: TaskDef, env: Environment) -> None:
        def run_task():
            task_env = Environment(parent=env)
            try:
                for stmt in node.body:
                    self.execute(stmt, task_env)
            except Exception:
                pass

        t = threading.Thread(target=run_task, daemon=True)
        t.start()
        self.tasks.append(t)

    def exec_EveryDef(self, node: EveryDef, env: Environment) -> None:
        def run_every():
            multipliers = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400}
            interval_val = self.evaluate(node.interval, env)
            seconds = float(interval_val) * multipliers.get(node.unit, 1)

            def tick():
                while True:
                    time.sleep(seconds)
                    every_env = Environment(parent=env)
                    try:
                        for stmt in node.body:
                            self.execute(stmt, every_env)
                    except Exception:
                        pass

            t = threading.Thread(target=tick, daemon=True)
            t.start()
            self.tasks.append(t)

        run_every()

    def exec_ImportStatement(self, node: ImportStatement, env: Environment) -> None:
        import_env, _ = self._load_module(node.path)
        for name, val in import_env.vars.items():
            env.vars[name] = val
        for name, func in import_env.functions.items():
            env.functions[name] = func

    def exec_FromImportStatement(self, node: FromImportStatement, env: Environment) -> None:
        import_env, _ = self._load_module(node.path)
        for name in node.names:
            if name in import_env.vars:
                env.vars[name] = import_env.vars[name]
            elif name in import_env.functions:
                env.functions[name] = import_env.functions[name]
            else:
                raise PapaError(
                    f"'{name}' не найден в модуле {node.path}",
                    line=node.line,
                    hint=f"Проверьте экспорт в файле {node.path}"
                )


__all__ = ['ExecutorMixin']
