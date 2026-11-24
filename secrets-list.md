# Секреты и переменные GitHub Actions

## Секреты репозитория

Добавь их в **Settings → Secrets and variables → Actions → Secrets → New repository secret**. [Документация GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

| Общий секрет | Значение |
| --- | --- |
| `SSH_HOST` | Адрес сервера деплоя |
| `SSH_PORT` | SSH-порт сервера |
| `SSH_USER` | Пользователь для деплоя |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ пользователя деплоя |
| `YC_SA_ID` | ID сервисного аккаунта Yandex Cloud для доступа к Container Registry |
| `YANDEX_OAUTH_CLIENT_SECRET` | Секрет OAuth-приложения Yandex для backend |

| Тестовый backend | Продакшен backend | Значение |
| --- | --- | --- |
| `TEST_DATABASE_URI` | `PROD_DATABASE_URI` | URI подключения к базе данных |
| `TEST_CACHE_URI` | `PROD_CACHE_URI` | URI подключения к кэшу |
| `TEST_SECRET_KEY` | `PROD_SECRET_KEY` | Секретный ключ приложения |
| `TEST_MAIL_SERVER` | `PROD_MAIL_SERVER` | Адрес SMTP-сервера |
| `TEST_MAIL_PORT` | `PROD_MAIL_PORT` | Порт SMTP-сервера |
| `TEST_MAIL_USERNAME` | `PROD_MAIL_USERNAME` | Имя пользователя SMTP |
| `TEST_MAIL_PASSWORD` | `PROD_MAIL_PASSWORD` | Пароль SMTP |

## Переменные окружений

В **Settings → Environments** создай `backend-test`, `backend-prod`, `frontend-test` и `frontend-prod`. В каждом окружении добавь переменные через **Environment variables → Add variable**. Используй имена из таблиц без префиксов. В test-окружениях укажи значения для деплоя из `develop`, в prod-окружениях — из `main`. [Документация GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables)

### Во всех четырёх окружениях

| Переменная | Значение |
| --- | --- |
| `CR_REGISTRY` | ID реестра Yandex Container Registry |
| `CR_REPOSITORY` | Имя репозитория образа внутри реестра |
| `COMPOSE_FILENAME` | `docker-compose.test.yml` для `backend-test`, `docker-compose.prod.yml` для `backend-prod`, `docker-compose.yml` для обоих frontend-окружений |
| `COMPOSE_DESTINATION_PATH` | Каталог на SSH-сервере, куда копируется Compose-файл |
| `PORT` | Порт сервиса на сервере |
| `PROJECT_NAME` | Имя Docker Compose-проекта. Для деплоев на одном сервере используй разные имена |

### Дополнительно в `backend-test` и `backend-prod`

| Переменная | Значение |
| --- | --- |
| `COMPOSE_FOLDER_PATH` | `docker/`, с завершающим слешем |
| `DOMAIN` | Домен backend |
| `FRONTEND_URL` | URL frontend |
| `CDN_URL` | URL CDN |
| `COOKIE_DOMAIN` | Домен cookie |
| `ACCESS_COOKIE_NAME` | Имя cookie токена доступа |
| `REFRESH_COOKIE_NAME` | Имя cookie токена обновления |
| `ACCESS_CSRF_COOKIE_NAME` | Имя CSRF-cookie для токена доступа |
| `REFRESH_CSRF_COOKIE_NAME` | Имя CSRF-cookie для токена обновления |
| `AUTH_PROFILE_COOKIE_NAME` | Имя cookie профиля |
| `MAIL_DEFAULT_SENDER` | Адрес отправителя по умолчанию |
| `UPLOAD_DIR` | Каталог загружаемых файлов на сервере |
| `LOG_DIR` | Каталог логов на сервере |
| `YANDEX_OAUTH_LOGIN_URL` | URL входа через Yandex OAuth |
| `YANDEX_AVATARS_URL` | Базовый URL аватаров Yandex |
| `YANDEX_AVATARS_SIZE` | Размер аватаров Yandex |

### Дополнительно в `frontend-test` и `frontend-prod`

| Переменная | Значение |
| --- | --- |
| `API_URL` | URL backend API, доступный из frontend-контейнера |
| `NEXT_PUBLIC_SITE_URL` | Публичный URL frontend |
| `NEXT_PUBLIC_CSRF_ACCESS_COOKIE_NAME` | Имя CSRF-cookie для токена доступа, как в `ACCESS_CSRF_COOKIE_NAME` соответствующего backend-окружения |
| `NEXT_PUBLIC_CSRF_REFRESH_COOKIE_NAME` | Имя CSRF-cookie для токена обновления, как в `REFRESH_CSRF_COOKIE_NAME` соответствующего backend-окружения |
| `NEXT_PUBLIC_YANDEX_OAUTH_CLIENT_ID` | Публичный ID OAuth-приложения Yandex |
| `NEXT_PUBLIC_YANDEX_OAUTH_REDIRECT_URL` | URL перенаправления после Yandex OAuth |
| `NEXT_PUBLIC_YANDEX_OAUTH_ORIGIN` | Origin для Yandex OAuth |

Переменные `NEXT_PUBLIC_*` передаются при сборке frontend-образа. Чтобы применить новые значения, пересобери образ.
