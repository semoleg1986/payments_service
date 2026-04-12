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

test-quick: ## Быстрый прогон тестов
	pytest -q

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

migrate: ## Применить миграции Alembic
	alembic upgrade head

makemigration: ## Создать миграцию Alembic (пример: make makemigration MSG=init)
	alembic revision --autogenerate -m "$(MSG)"

run: ## Запустить HTTP API локально
	uvicorn src.interface.http.main:app --host 0.0.0.0 --port 8004 --reload

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
