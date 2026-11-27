from celery import shared_task
from dependency_injector.wiring import Provide, inject

from kanwoo.unit_of_work import UnitOfWork

from .entity import ChapterPagesOptimizationStatus
from .repositories import ChapterRepository
from .services import ChapterPagesOptimizationService

MAKE_OPTIMIZE_CHAPTER_PAGES_TASKS_NAME = "kanwoo.chapter.tasks.make_optimize_chapter_pages_tasks"


@shared_task
@inject
def optimize_chapter_pages(
    chapter_id: int,
    *,
    repository: ChapterRepository = Provide["chapter_container.chapter_repo"],
    optimization: ChapterPagesOptimizationService = Provide["chapter_pages_optimization_service"],
    uow: UnitOfWork = Provide["unit_of_work"],
):
    waiting = ChapterPagesOptimizationStatus.WAITING.value
    completed = ChapterPagesOptimizationStatus.COMPLETED.value

    chapter = repository.get_chapter_by_id(chapter_id, public=False)
    if chapter is None or chapter.optimization_status_id != waiting:
        return

    original_pages = repository.get_chapter_original_pages(chapter.id)
    optimized_pages = {}
    for page in original_pages:
        if page.process_status_id == waiting:
            parts = optimization.optimize_page(page)
            optimized_pages[page.uuid] = parts

    with uow:
        chapter = repository.get_chapter_by_id(chapter_id, public=False, for_update=True)
        if chapter is None or chapter.optimization_status_id != waiting:
            return

        for page in chapter.chapter_pages:
            if page.is_orig and page.process_status_id == waiting and page.uuid not in optimized_pages:
                return

        for page in chapter.chapter_pages:
            if not page.is_orig or page.process_status_id != waiting:
                continue
            page.optimized_pages = optimized_pages[page.uuid]
            page.process_status_id = completed

        chapter.optimization_status_id = completed


@shared_task(name=MAKE_OPTIMIZE_CHAPTER_PAGES_TASKS_NAME)
@inject
def make_optimize_chapter_pages_tasks(
    *,
    optimization: ChapterPagesOptimizationService = Provide["chapter_pages_optimization_service"],
):
    for chapter_id in optimization.get_waiting_chapter_ids():
        optimization.enqueue_chapter(chapter_id)
