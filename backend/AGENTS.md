# Руководство по бэкенду

## Скрипты Poetry

Запускайте команды из каталога `backend` после установки зависимостей через `poetry install`. Для `dev`, `test` и `db_migrate` нужен запущенный Docker с Docker Compose.

| Команда | Что делает |
| --- | --- |
| `poetry run dev` | Поднимает сервисы из `docker/docker-compose.dev.yml`, применяет миграции, загружает начальные данные и запускает Flask на порту `5000`, Celery Worker и Celery Beat. При завершении останавливает процессы и сервисы Compose. |
| `poetry run test` | Поднимает сервисы из `docker/docker-compose.test.yml`, запускает `pytest` и останавливает сервисы после прогона. |
| `poetry run db_migrate -m "Описание миграции"` | Поднимает сервисы разработки, вызывает `flask db upgrade` для применения существующих миграций и генерирует новую через `flask db migrate`. Аргумент `-m` обязателен. |
| `poetry run db_upgrade` | Заглушка, которая выводит `db_upgrade`. Для применения миграций к настроенной и доступной базе используйте `poetry run flask db upgrade`. |
