# 🛡️ PAPA Lang v0.8.0

**Язык программирования нового поколения** — построен на анализе 10 ведущих языков, устраняет целые категории багов by design.

## Философия

| Проблема существующих языков | Решение в PAPA Lang |
|-----|-----|
| 3 вида строк (`'`, `"`, `` ` ``) | Один вид: `"строка с {подстановкой}"` |
| `null`, `undefined`, `NaN` | Тип `maybe` — значение или nothing |
| Пароли в логах и stack traces | Тип `secret` — автоматическая редакция |
| 7+ конфиг-файлов | Один `project.papa` |
| `if err != nil` на каждой строке | Маркер `!` на функции + `??` |
| Мутабельность по умолчанию | Иммутабельность по умолчанию, `mut` явно |
| `===` vs `==` vs `=` | `==` сравнение, `=` присвоение. Всё. |
| Скобки, точки с запятой | Отступы, без `;` |

## Быстрый старт

```bash
# Запуск программы
python3 papa.py run examples/05_full_demo.papa

# HTTP сервер (v0.3)
python3 papa.py serve examples/06_server.papa

# Интерактивная консоль
python3 papa.py repl

# Тесты
python3 papa.py test examples/05_full_demo.papa

# Показать токены (отладка)
python3 papa.py lex examples/01_hello.papa

# Показать AST (отладка)
python3 papa.py ast examples/01_hello.papa
```

## Примеры

### Hello World
```
say "Привет, мир!"
```

### Переменные и строки
```
name = "PAPA"
version = 3
say "Добро пожаловать в {name} v{version}!"
```

### Безопасность
```
// Maybe — нет null!
user = some("admin")
name = user ?? "аноним"

// Secret — пароли не утекают
password = secret("SuperSecret123!")
say "Пароль: {password}"
// → Пароль: ***REDACTED***

// Иммутабельность по умолчанию
server = "papa-ai.ae"
// server = "hacked.com"  ← Ошибка компиляции!
mut counter = 0            // ← Явно мутабельная
counter = counter + 1      // ✅ OK
```

### Функции
```
// Короткая форма
double(n: int) -> int = n * 2

// С телом
factorial(n: int) -> int
  if n <= 1
    return 1
  return n * factorial(n - 1)

say factorial(10)  // → 3628800
```

### HTTP сервер (v0.3)
```
serve on port 8200

route GET "/"
  do
    return "Hello from PAPA Lang!"

route GET "/users/:id"
  do
    return "User {id}"

route POST "/echo"
  do
    return body
```

### Импорты (v0.3)
```
import "std/math"
say sqrt(16)

from "utils.papa" import double, greet
say double(7)
```

### Model (v0.3)
```
model User
  name: text
  email: text unique
  age: int

user = User.create(name: "Иван", email: "ivan@test.com", age: 25)
all_users = User.all()
found = User.find(email: "ivan@test.com")
adults = User.where(age >= 18)
```

### Task и Every (v0.3)
```
task cleanup
  say "Cleaning..."

every 5 seconds
  say "Tick at {now()}"
```

### Тесты
```
test "математика работает"
  assert 2 + 2 == 4
  assert double(21) == 42

test "secret скрывает значение"
  pw = secret("test")
  assert "{pw}" == "***REDACTED***"
```

### Дружественные ошибки
```
say 'hello'
// ── ОШИБКА ЛЕКСЕРА в строке 1 ──
//   say 'hello'
//       ^^^
//   В PAPA Lang используются только двойные кавычки "..."
//   Замените ' на "
```

## Стандартная библиотека (18 модулей)

| Модуль | Описание |
|--------|----------|
| `std/math` | sqrt, pow, floor, ceil, sin, cos, random |
| `std/string` | upper, lower, trim, split, join, replace |
| `std/json` | json_encode, json_decode |
| `std/http` | http_get, http_post |
| `std/fs` | read_file, write_file, file_exists |
| `std/time` | timestamp, format_time, sleep |
| `std/voice` | voice_call, voice_sms, voice_tts — Telnyx |
| `std/mcp` | MCP connectors — Composio, email, calendar |
| `std/browser` | browser automation, scraping, screenshots |
| `std/telegram` | Telegram Bot API — messaging, commands |
| `std/ai` | ai_budget — cost guardrails |
| `std/design` | AI design — tokens, components, palettes |

## Структура проекта

```
papa-lang/
  papa.py              — CLI: papa run, papa serve, papa repl, papa test
  repl.py              — Интерактивная консоль
  src/
    __init__.py        — Пакет
    lexer.py           — Лексер (токенизация)
    parser.py          — Парсер (AST)
    ast_nodes.py       — Узлы AST
    interpreter.py     — Интерпретатор
  std/
    math.papa          — Стандартная библиотека: sqrt, floor, ceil, pow
    string.papa        — Стандартная библиотека: join, split
  examples/
    01_hello.papa      — Hello World
    02_safety.papa     — Безопасность: maybe, secret
    03_functions.papa  — Функции и циклы
    04_server.papa     — Веб-сервер (симуляция)
    05_full_demo.papa  — Полная демонстрация
    06_server.papa     — HTTP сервер (работающий)
    07_imports.papa    — Импорты
    08_async.papa      — Task и Every
    09_models.papa     — Model/Store
```

## Roadmap

- [x] Встроенный HTTP сервер (v0.3)
- [x] Встроенная ORM / Model (v0.3)
- [ ] Компиляция в native (LLVM backend)
- [ ] Компиляция в WASM (браузер)
- [ ] Пакетный менеджер
- [ ] LSP для IDE
- [ ] Playground в браузере

## Лицензия

MIT — Mura Menasa FZCO, Dubai
