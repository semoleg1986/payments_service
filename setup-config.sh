#!/bin/bash

touch README.md

# Создаём структуру приложения
mkdir -p src/{domain,application,infrastructure}
touch src/__init__.py
touch src/domain/__init__.py
touch src/application/__init__.py
touch src/infrastructure/__init__.py

# Создаём каталог для тестов
mkdir -p tests
cat > tests/test_example.py <<'EOF'
import pytest

def test_dummy():
    assert True
EOF

# Создаём .gitkeep файлы (опционально) чтобы git отслеживал пустые папки
touch src/domain/.gitkeep
touch src/application/.gitkeep
touch src/infrastructure/.gitkeep



cat > Makefile <<'EOF'
# ========================
# Requirements
# ========================

requirements: ## Скомпилировать requirements.in в requirements.txt
	pip-compile requirements.in

install: requirements ## Установить зависимости
	pip install -r requirements.txt

# ========================
# Test
# ========================

test: ## Запустить все тесты с подробным выводом
	pytest -v

# ========================
# Code Quality
# ========================

format: ## Автоматическое форматирование кода (isort + black)
	isort .
	black .

lint: ## Проверка стиля и типов (flake8 + mypy)
	flake8 .
	mypy .

check: format lint test ## Полная проверка качества кода

# ========================
# Pre-commit
# ========================

precommit: ## Запуск pre-commit хуков на всех файлах
	pre-commit run --all-files

# ========================
# Help
# ========================

help: ## Показать список доступных команд
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| sort \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
EOF

cat >  requirements.in <<EOF
pytest

black
isort
flake8
mypy

pre-commit
EOF

cat > .gitignore <<EOF
# Python
.venv/
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.pytest_cache/
*.sqlite3

# IDE and OS
.idea/
*.swp
.DS_Store
.env
.copy.env
EOF

cat > pyproject.toml <<'EOF'
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.venv
  | \.git
  | __pycache__
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
EOF


cat > .flake8 <<EOF
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .venv,
    __pycache__,
    build,
    dist
EOF

cat > pytest.ini <<EOF
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
EOF

cat > mypy.ini  <<EOF
[mypy]
python_version = 3.11
ignore_missing_imports = True
ignore_errors = True
strict = True
exclude = (venv|\.venv|__pycache__)
EOF

cat > .pre-commit-config.yaml <<EOF
repos:
  # --- Импорт и сортировка ---
  - repo: https://github.com/pre-commit/mirrors-isort
    rev: v5.10.1
    hooks:
      - id: isort
  # --- Автоформатирование кода ---
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  # --- Проверка стиля и ошибок ---
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8

  # --- Проверка типов ---
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        args: [ "--install-types", "--non-interactive" ]

  # --- Локальный хук для тестов ---
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests
        language: system
        pass_filenames: false
EOF


echo "Минимальная структура проекта создана:"

tree || ls -R