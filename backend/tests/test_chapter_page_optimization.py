from io import BytesIO
from unittest.mock import Mock, call
from uuid import UUID, uuid4

import pytest
from flask import Flask
from kombu.exceptions import OperationalError
from PIL import Image

from kanwoo import db
from kanwoo.celery import celery_init_app, setup_celery
from kanwoo.chapter.entity import ChapterPagesOptimizationStatus
from kanwoo.chapter.models import Chapter, ChapterPage, OptimizedPage, Page
from kanwoo.chapter.services import ChapterPagesOptimizationService
from kanwoo.chapter.tasks import make_optimize_chapter_pages_tasks, optimize_chapter_pages
from kanwoo.containers import AppContainer
from kanwoo.entities import File
from kanwoo.image import ImageServiceFactory
from kanwoo.models import FileModel
from kanwoo.unit_of_work import UnitOfWork


@pytest.mark.parametrize(
    ("source_size", "expected_heights"),
    [
        ((500, 707), [1414]),
        ((1000, 1415), [1415]),
        ((1000, 1500), [1500]),
        ((500, 800), [800, 800]),
        ((1000, 1501), [750, 751]),
        ((1000, 3001), [1000, 1000, 1001]),
    ],
)
def test_optimize_page(source_size, expected_heights):
    with Image.new("RGB", source_size, "red") as source, BytesIO() as buffer:
        source.paste("blue", (0, source.height // 2, source.width, source.height))
        source.save(buffer, format="PNG")
        source_file = File("page.png", "image/png", buffer.getvalue())

    storage = Mock()
    storage.read.return_value = source_file
    service = ChapterPagesOptimizationService(storage, ImageServiceFactory(), Mock())
    original = ChapterPage(
        chapter_id=4,
        file=FileModel(uuid="original", path="chapters/original", filename="page.png", mimetype="image/png"),
    )

    parts = service.optimize_page(original)

    storage.read.assert_called_once_with(original.path)
    assert [part.height for part in parts] == expected_heights
    assert [part.order for part in parts] == list(range(len(parts)))
    assert storage.save.call_count == len(parts)
    for part, saved in zip(parts, storage.save.call_args_list, strict=True):
        file, key = saved.args
        assert key == part.path
        assert UUID(part.uuid).version == 4
        assert key == f"chapters/optimized/{part.uuid}"
        assert file.content_type == "image/webp"
        assert part.file.mimetype == "image/webp"
        assert part.file.file_size == len(file.bytes)
        with Image.open(BytesIO(file.bytes)) as image:
            assert image.format == "WEBP"
            assert image.size == (1000, part.height)
    first_file = storage.save.call_args_list[0].args[0]
    last_file = storage.save.call_args_list[-1].args[0]
    with Image.open(BytesIO(first_file.bytes)) as first, Image.open(BytesIO(last_file.bytes)) as last:
        assert first.getpixel((500, 0))[0] > 200
        assert last.getpixel((500, last.height - 1))[2] > 200

    retried = service.optimize_page(original)
    assert {part.path for part in parts}.isdisjoint(part.path for part in retried)


@pytest.fixture
def task_app():
    app = Flask(__name__)
    app.config["CELERY"] = {"broker_url": "memory:"}
    container = AppContainer()
    container.db_session.override(Mock())
    container.chapter_container.chapter_repo.override(Mock())
    container.chapter_pages_optimization_service.override(Mock())
    container.wire(modules=["kanwoo.chapter.tasks"])
    app.container = container
    celery_app = celery_init_app(app)
    setup_celery(celery_app, app.config["CELERY"])
    yield app
    with app.app_context():
        container.unwire()


def test_task_replaces_pending_pages_in_order_and_skips_completed_chapter(task_app):
    repository = task_app.container.chapter_container.chapter_repo()
    waiting = ChapterPagesOptimizationStatus.WAITING.value
    completed = ChapterPagesOptimizationStatus.COMPLETED.value
    first = ChapterPage(order=0, is_orig=True, file=FileModel(uuid="first"), process_status_id=waiting)
    legacy = Page(order=1, uuid="legacy")
    retained = OptimizedPage(order=0)
    second = ChapterPage(
        order=2, is_orig=True, file=FileModel(uuid="second"),
        process_status_id=completed, optimized_pages=[retained],
    )
    chapter = Chapter(
        id=7,
        optimization_status_id=waiting,
        chapter_pages=[first, second],
        legacy_pages=[legacy],
    )
    repository.get_chapter_by_id.return_value = chapter
    repository.get_chapter_original_pages.return_value = [second, first]
    optimize_page = task_app.container.chapter_pages_optimization_service().optimize_page
    first_parts = [OptimizedPage(order=0), OptimizedPage(order=1)]
    optimize_page.return_value = first_parts

    optimize_chapter_pages(7)
    optimize_chapter_pages(7)

    assert repository.get_chapter_by_id.call_args_list == [
        call(7, public=False),
        call(7, public=False, for_update=True),
        call(7, public=False),
    ]
    repository.get_chapter_original_pages.assert_called_once_with(7)
    optimize_page.assert_called_once_with(first)
    assert chapter.chapter_pages == [first, second]
    assert first.optimized_pages == first_parts
    assert second.optimized_pages == [retained]
    assert chapter.pages == [*first_parts, legacy, retained]
    assert [page.order for page in chapter.pages] == [0, 1, 1, 0]
    assert [first.order, second.order] == [0, 2]
    assert chapter.studio_pages == [first, legacy, second]
    assert first.process_status_id == second.process_status_id == completed
    assert chapter.optimization_status_id == completed
    task_app.container.db_session().commit.assert_called_once()


def test_task_does_not_start_write_transaction_when_storage_fails(task_app):
    repository = task_app.container.chapter_container.chapter_repo()
    waiting = ChapterPagesOptimizationStatus.WAITING.value
    chapter = Chapter(
        id=7,
        optimization_status_id=waiting,
        chapter_pages=[
            ChapterPage(order=order, is_orig=True, file=FileModel(uuid=str(order)), process_status_id=waiting)
            for order in range(2)
        ],
    )
    repository.get_chapter_by_id.return_value = chapter
    repository.get_chapter_original_pages.return_value = chapter.chapter_pages
    optimize_page = task_app.container.chapter_pages_optimization_service().optimize_page
    optimize_page.side_effect = [[OptimizedPage(order=0)], OSError("S3 failed")]

    with pytest.raises(OSError, match="S3 failed"):
        optimize_chapter_pages(7)

    task_app.container.db_session().commit.assert_not_called()
    repository.get_chapter_by_id.assert_called_once_with(7, public=False)
    assert chapter.optimization_status_id == waiting
    assert all(page.process_status_id == waiting and not page.optimized_pages for page in chapter.chapter_pages)


@pytest.mark.parametrize("chapter_completed", [False, True])
def test_task_does_not_write_stale_results(task_app, chapter_completed):
    repository = task_app.container.chapter_container.chapter_repo()
    waiting = ChapterPagesOptimizationStatus.WAITING.value
    completed = ChapterPagesOptimizationStatus.COMPLETED.value
    source = ChapterPage(file=FileModel(uuid="original"), is_orig=True, process_status_id=waiting)
    added = ChapterPage(file=FileModel(uuid="added"), is_orig=True, process_status_id=waiting)
    before = Chapter(id=7, optimization_status_id=waiting)
    after = Chapter(
        id=7,
        optimization_status_id=completed if chapter_completed else waiting,
        chapter_pages=[source, added],
    )
    repository.get_chapter_by_id.side_effect = [before, after]
    repository.get_chapter_original_pages.return_value = [source]
    optimize_page = task_app.container.chapter_pages_optimization_service().optimize_page
    optimize_page.return_value = [OptimizedPage(order=0)]

    optimize_chapter_pages(7)

    optimize_page.assert_called_once_with(source)
    assert after.optimization_status_id == (completed if chapter_completed else waiting)
    assert all(page.process_status_id == waiting and not page.optimized_pages for page in after.chapter_pages)


def test_task_persists_page_parts_after_retry(app, profile_id):
    waiting = ChapterPagesOptimizationStatus.WAITING.value
    completed = ChapterPagesOptimizationStatus.COMPLETED.value
    with app.app_context():
        chapter = Chapter(
            chapter=1,
            creator_id=profile_id,
            optimization_status_id=waiting,
            chapter_pages=[
                ChapterPage(
                    file=FileModel(uuid=str(uuid4()), path=f"chapters/source-{order}", mimetype="image/png"),
                    width=500,
                    height=800,
                    order=order,
                    is_orig=True,
                    process_status_id=waiting,
                )
                for order in range(2)
            ],
        )
        db.session.add(chapter)
        db.session.commit()
        chapter_id = chapter.id
        source_ids = [page.file_uuid for page in chapter.chapter_pages]

    with Image.new("RGB", (500, 800), "red") as image, BytesIO() as buffer:
        image.save(buffer, format="PNG")
        source_file = File("page.png", "image/png", buffer.getvalue())
    storage = Mock()
    storage.read.return_value = source_file
    storage.save.side_effect = [None, None, OSError("storage unavailable")]

    with app.container.object_storage.override(storage):
        with pytest.raises(OSError, match="storage unavailable"):
            optimize_chapter_pages(chapter_id)

        with app.app_context():
            chapter = db.session.get(Chapter, chapter_id)
            assert chapter.optimization_status_id == waiting
            assert [page.file_uuid for page in chapter.pages] == source_ids
            assert all(not page.optimized_pages for page in chapter.chapter_pages)

        storage.save.side_effect = None
        storage.save.reset_mock()
        optimize_chapter_pages(chapter_id)
        optimize_chapter_pages(chapter_id)

    assert storage.save.call_count == 4
    with app.app_context():
        chapter = db.session.get(Chapter, chapter_id)
        assert chapter.optimization_status_id == completed
        assert [page.file_uuid for page in chapter.studio_pages] == source_ids
        assert [page.process_status_id for page in chapter.chapter_pages] == [completed, completed]
        assert [page.order for page in chapter.chapter_pages] == [0, 1]
        assert [page.order for page in chapter.pages] == [0, 1, 0, 1]
        assert [page.source_uuid for page in chapter.pages] == [
            source_ids[0], source_ids[0], source_ids[1], source_ids[1],
        ]


@pytest.mark.parametrize("first_error", [None, OperationalError("broker unavailable")])
def test_hourly_task_queues_waiting_chapters(task_app, monkeypatch, first_error):
    repository = Mock()
    repository.get_waiting_optimization_ids.return_value = [7, 9]
    task_app.container.chapter_pages_optimization_service.override(
        ChapterPagesOptimizationService(Mock(), ImageServiceFactory(), repository)
    )
    celery = task_app.extensions["celery"]
    enqueue = Mock(side_effect=[first_error, None])
    monkeypatch.setattr(celery.tasks[optimize_chapter_pages.name], "delay", enqueue)
    schedule = celery.conf.beat_schedule["optimize-waiting-chapters-hourly"]
    assert schedule["schedule"] == 3600
    assert schedule["task"] == make_optimize_chapter_pages_tasks.name

    celery.tasks[schedule["task"]]()

    repository.get_waiting_optimization_ids.assert_called_once_with()
    assert enqueue.call_args_list == [call(7), call(9)]


def test_after_commit_waits_for_outer_uow_and_drops_callback_on_rollback():
    session = Mock()
    callback = Mock()
    with UnitOfWork(session):
        with UnitOfWork(session) as inner:
            inner.after_commit(callback)
        callback.assert_not_called()

    session.commit.assert_called_once()
    callback.assert_called_once()
    callback.reset_mock()

    with pytest.raises(ValueError):
        with UnitOfWork(session):
            with UnitOfWork(session) as inner:
                inner.after_commit(callback)
            raise ValueError("rollback")
    session.rollback.assert_called_once()
    callback.assert_not_called()
