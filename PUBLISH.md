# Публикация пакетов papa-lang

## Порядок (строгий)

1. **papa-guard** — без зависимостей от нас
2. **papa-lang** — зависит от papa-guard
3. **papa-rag** — зависит от papa-lang
4. **@papa-lang/core** — npm, независимый

---

## Быстрый старт

### 1. Токены

Создайте `.env.publish` из примера:

```bash
cp .env.publish.example .env.publish
# Отредактируйте .env.publish — добавьте реальные токены
```

- **TestPyPI**: [test.pypi.org/manage/account/token/](https://test.pypi.org/manage/account/token/) — `username=__token__`, `password=pypi-xxx`
- **PyPI**: [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)
- **npm**: `npm token create` или из `~/.npmrc`

### 2. Тест (TestPyPI)

```bash
# Заполните .env.publish токеном TestPyPI
source .env.publish
TEST=1 ./scripts/publish_with_env.sh
```

Проверка установки:

```bash
pip install --index-url https://test.pypi.org/simple/ papa-guard
```

### 3. Продакшн

```bash
source .env.publish
./scripts/publish_with_env.sh
```

### 4. git push

```bash
# Добавить хост (если нужно)
ssh-keyscan git.papa-ai.ae >> ~/.ssh/known_hosts

# SSH ключ должен быть добавлен в git.papa-ai.ae
git push -u origin main
```

---

## Итог экосистемы

| Шаг            | Статус                          |
|----------------|---------------------------------|
| papa-guard 0.1.0 | ✅ Собран локально              |
| papa-lang, papa-rag | ✅ Собран локально           |
| @papa-lang/core | ✅ Собран (npm run build)        |
| git push       | ⏳ SSH key в git.papa-ai.ae     |
| PyPI           | ⏳ twine upload (нужен токен)    |
| npm            | ⏳ npm publish (нужен npm login) |
