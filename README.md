[![CI](https://github.com/Catorol/PythEngin/actions/workflows/ci.yml/badge.svg)](https://github.com/Catorol/PythEngin/actions)

# research-graph

[![CI](https://github.com/Catorol/PythEngin/actions/workflows/ci.yml/badge.svg)](https://github.com/Catorol/PythEngin/actions)

ОПИСАНИЕ ВРЕМЕННО ОТСУСТВУЕТ

Проект развивается на протяжении семестра, в каждой лабораторной добавляется новая часть.

## Требования

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — менеджер зависимостей и окружений

## Установка

```bash
git clone https://github.com/Catorol/PythEngin.git
cd /PythEngin
uv sync
```

Проверка, что всё работает:

```bash
uv run rg version
```

## Конфигурация

Настройки читаются из переменных окружения с префиксом `RG_`.

| Переменная | Описание | По умолчанию | Ограничения |
|---|---|---|---|
| `RG_GITHUB_TOKEN` | Токен GitHub (в выводе маскируется) | не задан | — |
| `RG_DATA_DIR` | Каталог для данных | `data` | — |
| `RG_LOG_LEVEL` | Уровень логирования | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `RG_REQUEST_TIMEOUT` | Таймаут запросов, секунды | `30.0` | больше 0, не больше 300 |
| `RG_MAX_CONCURRENCY` | Максимум параллельных задач | `8` | от 1 до 64 |

Пример:

```bash
export RG_LOG_LEVEL=DEBUG
export RG_MAX_CONCURRENCY=16
```

## Использование

Список команд:

```bash
uv run rg --help
```

```
version   Показать версию пакета.

check-config  Загрузить настройки и показать сводку (токен маскируется).
```


Версия пакета:

```bash
uv run rg version
```

```
0.1.0
```

Проверка конфигурации:

```bash
uv run rg check-config
```

```
data_dir:         data
log_level:        INFO
request_timeout:  30.0
max_concurrency:  8
github_token:     не задан
```

Если задан токен, показываются только первые и последние 4 символа:

```bash
RG_GITHUB_TOKEN=ghp_supersecretvalue uv run rg check-config
```

```
...
github_token:     ghp_****alue
```

## Разработка

```bash
uv run pytest                    # тесты и покрытие
uv run ruff check .              # линтер
uv run ruff format .             # форматирование
uv run mypy                      # проверка типов
uv run pre-commit run --all-files   # все проверки сразу
```

Перед первой работой один раз выполните `uv run pre-commit install`, чтобы проверки запускались при каждом коммите.

## Структура проекта

```
.
├── .github/workflows/ci.yml      # непрерывная интеграция
├── .pre-commit-config.yaml       # хуки перед коммитом
├── .python-version               # версия Python
├── docs/
│   └── lab1_report.md            # отчёт по ЛР1
├── pyproject.toml                # зависимости и настройки инструментов
├── uv.lock                       # зафиксированные версии зависимостей
├── src/research_graph/
│   ├── __init__.py
│   ├── cli.py                    # CLI (команда rg)
│   ├── config.py                 # настройки (RG_*)
│   └── logging_setup.py          # настройка логирования
└── tests/
    ├── conftest.py               # изоляция тестов от окружения
    ├── test_cli.py
    ├── test_config.py
    └── test_logging.py
```
