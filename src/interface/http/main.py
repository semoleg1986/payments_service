"""Точка входа HTTP приложения."""

from __future__ import annotations

from src.interface.http.app import create_app

app = create_app()
