from flask import Flask

from kanwoo.exceptions import setup_exceptions
from kanwoo.logs import setup_logs

from kanwoo import AppContainer
from kanwoo import (
    db, migrate, mail, cors, file_storage, limiter, cache, jwt_manager
)
from kanwoo.celery import celery_init_app, setup_celery
from kanwoo.jwt import setup_jwt_error_handlers
from kanwoo.routes import setup_routes
from kanwoo.file_storage import S3Storage
# from kanwoo.middleware import setup_middleware


def create_app(config):
    container = AppContainer()
    container.wire(packages=[
        "kanwoo",
        "kanwoo.reading_progress"
    ])

    app = Flask(__name__)
    app.config.from_object(config)

    container.config.from_dict(app.config)
    app.container = container

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt_manager.init_app(app)
    cors.init_app(app)
    file_storage.init_app(app)
    if app.config.get("S3_BUCKET_NAME"):
        container.object_storage.override(S3Storage(app))
    limiter.init_app(app)
    cache.init_app(app)

    # Инициализация celery
    app.config["CELERY"] = {
        "broker_url": "redis://localhost",
        "task_ignore_result": True,
        "worker_concurrency": 1,
        "worker_prefetch_multiplier": 1,
        **app.config.get("CELERY", {}),
    }
    app.config.from_prefixed_env()
    if broker_uri := app.config.get("CELERY_BROKERY_URI"):
        app.config["CELERY"]["broker_url"] = broker_uri
    celery_app = celery_init_app(app)
    setup_celery(celery_app, app.config["CELERY"])

    container.db_session.override(db.session)
    container.file_storage.override(file_storage)
    container.cache.override(cache)

    setup_routes(app)
    setup_exceptions(app)
    # setup_middleware(app)
    setup_logs(app)
    setup_jwt_error_handlers(jwt_manager)

    return app
