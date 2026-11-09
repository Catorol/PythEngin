#!/bin/sh
set -e

echo "==> Миграции"
alembic upgrade head

echo "==> Импорт данных (идемпотентно)"
python -m research_graph.etl.import_data --source data/sample/tiktok_sample.csv

echo "==> Регистрация базовой модели"
rg register-model --path models/model.pkl

echo "==> Запуск API"
exec uvicorn research_graph.main:app --host 0.0.0.0 --port 8000
