from collections.abc import Mapping

from celery import Celery, Task
from flask import Flask

from kanwoo.chapter.tasks import MAKE_OPTIMIZE_CHAPTER_PAGES_TASKS_NAME


def celery_init_app(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    app.extensions["celery"] = celery_app
    return celery_app


def setup_celery(celery_app: Celery, config: Mapping[str, object]) -> None:
    celery_app.set_default()

    @celery_app.on_after_configure.connect(sender=celery_app, weak=False)
    def setup_periodic_tasks(sender: Celery, **kwargs: object) -> None:
        sender.add_periodic_task(
            3600,
            sender.signature(MAKE_OPTIMIZE_CHAPTER_PAGES_TASKS_NAME),
            name="optimize-waiting-chapters-hourly",
        )

    celery_app.config_from_object(config, force=True)
