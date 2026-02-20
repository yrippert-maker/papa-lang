"""
PAPA Lang Package Manager — v0.4
Установка локальных пакетов в papa_modules/.
Удалённый реестр — v0.5.
"""

import os
import shutil

PAPA_TOML_TEMPLATE = '''[project]
name = "my-app"
version = "0.1.0"
author = ""

[dependencies]
# Добавьте зависимости через: papa install <path>
'''


class PackageManager:
    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()
        self.papa_toml = os.path.join(self.cwd, "papa.toml")
        self.modules_dir = os.path.join(self.cwd, "papa_modules")

    def init(self) -> None:
        """Создать papa.toml с шаблоном."""
        if os.path.exists(self.papa_toml):
            print(f"  papa.toml уже существует в {self.cwd}")
            return
        with open(self.papa_toml, "w", encoding="utf-8") as f:
            f.write(PAPA_TOML_TEMPLATE)
        print(f"  Создан papa.toml в {self.cwd}")

    def install(self, package_path: str = None) -> None:
        """Установить пакет из локального пути или все из papa.toml."""
        if package_path:
            # Установка из локальной папки
            src = os.path.normpath(os.path.join(self.cwd, package_path))
            if not os.path.isdir(src):
                src = package_path
            if not os.path.isdir(src):
                print(f"\n── ОШИБКА ──\n\n  Путь не найден: {package_path}\n")
                return
            # Имя пакета из papa.toml или из имени папки
            toml_path = os.path.join(src, "papa.toml")
            if os.path.exists(toml_path):
                try:
                    import tomllib
                    with open(toml_path, "rb") as f:
                        data = tomllib.load(f)
                    name = data.get("project", {}).get("name", os.path.basename(src.rstrip(os.sep)))
                except ImportError:
                    name = os.path.basename(src.rstrip(os.sep))
            else:
                name = os.path.basename(src.rstrip(os.sep))
            dest = os.path.join(self.modules_dir, name)
            os.makedirs(self.modules_dir, exist_ok=True)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest, ignore=lambda d, files: [f for f in files if f == ".git"])
            print(f"  Установлен пакет '{name}' в papa_modules/")
        else:
            # Установить все из papa.toml
            if not os.path.exists(self.papa_toml):
                print(f"\n── ОШИБКА ──\n\n  papa.toml не найден. Выполните: papa init\n")
                return
            try:
                import tomllib
                with open(self.papa_toml, "rb") as f:
                    data = tomllib.load(f)
            except ImportError:
                import re
                data = {"dependencies": {}}
                in_deps = False
                for line in open(self.papa_toml, encoding="utf-8"):
                    line = line.strip()
                    if line == "[dependencies]":
                        in_deps = True
                        continue
                    if line.startswith("[") and line != "[dependencies]":
                        in_deps = False
                    if in_deps and "=" in line and not line.startswith("#"):
                        m = re.match(r'(\w+)\s*=\s*["\']?(.+?)["\']?\s*(#.*)?$', line)
                        if m:
                            data["dependencies"][m.group(1)] = m.group(2).strip().strip('"\'')
            deps = data.get("dependencies", {})
            if isinstance(deps, dict) and deps:
                for dep, path in deps.items():
                    if path:
                        self.install(path)
            else:
                print("  [dependencies] пуст — нечего устанавливать")

    def list_packages(self) -> list:
        """Список установленных пакетов в papa_modules/."""
        if not os.path.isdir(self.modules_dir):
            return []
        result = []
        for name in sorted(os.listdir(self.modules_dir)):
            path = os.path.join(self.modules_dir, name)
            if os.path.isdir(path):
                toml_path = os.path.join(path, "papa.toml")
                version = ""
                if os.path.exists(toml_path):
                    try:
                        import tomllib
                        with open(toml_path, "rb") as f:
                            data = tomllib.load(f)
                        version = data.get("project", {}).get("version", "")
                    except Exception:
                        version = ""
                result.append((name, version))
        return result

    def uninstall(self, name: str) -> None:
        """Удалить пакет из papa_modules/."""
        dest = os.path.join(self.modules_dir, name)
        if not os.path.isdir(dest):
            print(f"\n── ОШИБКА ──\n\n  Пакет '{name}' не установлен\n")
            return
        shutil.rmtree(dest)
        print(f"  Удалён пакет '{name}'")
