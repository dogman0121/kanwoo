from typing import Iterator, TYPE_CHECKING
import time
from flask import current_app
from kombu.exceptions import OperationalError
from kanwoo import db
from kanwoo.file_storage import OPTIMIZED_CHAPTER_OBJECT_PREFIX, FileStorageMixin, S3Storage
from kanwoo.uuid import UUIDGenerator
from kanwoo.image import ImageServiceFactory, Img
from kanwoo.models import FileModel
from kanwoo.entities import File
from kanwoo.database import DBTransaction
from kanwoo.unit_of_work import UnitOfWork
from kanwoo.frontend_metadata import FrontendMetadataServiceMixin, FrontendMetadataDTO, FrontentMetadataResouceTypeEnum

from .repositories import ChapterRepository
from .models import Chapter, ChapterPage, OptimizedPage, Page
from .dto import UpdateChapterDTO, ChapterContextDTO, CreateChapterDTO
from .exceptions import ChapterNotFoundException, ChapterWithNumberAlreadyExists, ChapterDeleteNotAllowed, ChapterUpdateNotAllowed
from .permissions import ChapterPolicy

class ChapterPageService:

    def __init__(
            self, 
            file_storage: FileStorageMixin, 
            image_service_factory: ImageServiceFactory, 
            chapter_repo: ChapterRepository
        ):
        self.file_storage = file_storage
        self.image_service_factory = image_service_factory
        self.chapter_repo = chapter_repo

    def __get_page_path(self, uuid, ext):
        return f"pages/{uuid}{ext}"

    def create_page(self, chapter, page_file, order):
        page_filename, _ = page_file.filename.rsplit(".", 1)
        page_uuid = UUIDGenerator.generate_uuid_v4()

        image_service = self.image_service_factory.create(page_file, output_format="WEBP")
        
        page_resized_file = image_service.resize((1280, 1000000))

        self.file_storage.save(page_resized_file, self.__get_page_path(page_uuid, ".webp"))
        
        page = Page(
            uuid=page_uuid,
            order = order,
            orig_filename = page_filename,
            width=page_resized_file.width,
            height=page_resized_file.height,
            path=self.__get_page_path(page_uuid, ".webp")
        )

        chapter.legacy_pages.append(page)

    def delete_page(self, page):
        self.chapter_repo.delete_page(page)

class ChapterService:

    def __init__(
            self, 
            db_transaction: DBTransaction,
            chapter_page_service: ChapterPageService, 
            chapter_repo: ChapterRepository,
            chapter_policy: ChapterPolicy,
            unit_of_work: UnitOfWork,
            pages_optimization_service: "ChapterPagesOptimizationService",
        ):
        self.chapter_repo = chapter_repo
        self.chapter_page_service = chapter_page_service
        self.chapter_policy = chapter_policy
        self.db_transaction = db_transaction
        self.unit_of_work = unit_of_work
        self.pages_optimization_service = pages_optimization_service

    def _delete_chapter(self, chapter: Chapter):
        self.chapter_repo.delete_chapter(chapter)

    def system_get_chapter_by_id(self, chapter_id):
        chapter = self.chapter_repo.get_chapter_by_id(chapter_id)

        if chapter is None:
            raise ChapterNotFoundException()

        return chapter
    
    def user_get_chapter_by_id(self, profile, chapter_id, by_link=False):
        chapter = self.chapter_repo.get_chapter_by_id_from_user(profile, chapter_id, by_link=by_link)

        if chapter is None:
            raise ChapterNotFoundException()

        return chapter

    def user_create_chapter(self, actor, translation, data: CreateChapterDTO):
        chapter_with_same_number_exists = self.chapter_repo.check_chapter_with_number(translation.id, data.chapter, data.extra_number)
        if chapter_with_same_number_exists:
            raise ChapterWithNumberAlreadyExists()
        
        with self.unit_of_work:
            chapter = Chapter(
                name=data.name,
                chapter=data.chapter,
                translation_id=translation.id,
                creator_id=actor.id,
                extra_number=data.extra_number,
                privacy_id=data.privacy_id,
            )

            for page_file in data.pages:
                page_filename = page_file.filename

                page_order = data.pages_order.index(page_filename)

                self.chapter_page_service.create_page(chapter, page_file, page_order)

            self.chapter_repo.create_chapter(chapter)
            
            return chapter
    
    def user_get_translation_chapters(self, actor, translation):
        chapters = self.chapter_repo.get_translation_chapters(translation.id)

        return chapters
    
    def system_update_pages(self, chapter: Chapter, pages: list[File], pages_order: list[str]):
        with self.db_transaction:
            uses_chapter_pages = bool(chapter.chapter_pages)
            ordered_pages: dict[int, File | Page | ChapterPage | OptimizedPage] = {}
            for existing_page in chapter.pages:
                try:
                    ordered_pages[pages_order.index(existing_page.uuid)] = existing_page
                except ValueError:
                    if isinstance(existing_page, OptimizedPage):
                        source = existing_page.source_page
                        source.optimized_pages.remove(existing_page)
                        if not source.optimized_pages:
                            chapter.chapter_pages.remove(source)
                    elif isinstance(existing_page, ChapterPage):
                        chapter.chapter_pages.remove(existing_page)
                    else:
                        self.chapter_page_service.delete_page(existing_page)

            for new_page in pages:
                ordered_pages[pages_order.index(new_page.filename)] = new_page

            order = 0
            next_part_order = {}
            for index in sorted(ordered_pages):
                page = ordered_pages[index]
                if isinstance(page, OptimizedPage):
                    source = page.source_page
                    if source not in next_part_order:
                        source.order = order
                        order += 1
                        next_part_order[source] = 0
                    page.order = next_part_order[source]
                    next_part_order[source] += 1
                elif not isinstance(page, File):
                    page.order = order
                    order += 1
                elif uses_chapter_pages:
                    parts = self.pages_optimization_service.optimize_file(page)
                    chapter.chapter_pages.extend(
                        ChapterPage(file=part.file, width=part.width, height=part.height, order=order + part.order)
                        for part in parts
                    )
                    order += len(parts)
                else:
                    self.chapter_page_service.create_page(chapter, page, order)
                    order += 1

    
    def user_update_chapter(self, profile, chapter: Chapter, data: UpdateChapterDTO):
        if not self.chapter_policy.can_edit(profile, chapter):
            raise ChapterUpdateNotAllowed()

        chapter_with_same_number_exists = self.chapter_repo.check_chapter_with_number(chapter.translation_id, data.chapter, data.extra_number)
        if chapter.chapter != data.chapter and chapter_with_same_number_exists:
            raise ChapterWithNumberAlreadyExists()

        with self.db_transaction:
            self.system_update_pages(chapter, data.pages, data.pages_order)

            updated_chapter = self.chapter_repo.update_chapter(chapter, {
                "name": data.name,
                "chapter": data.chapter,
                "privacy_id": data.privacy_id,
                "extra_number": data.extra_number,
            })

        return updated_chapter

    def system_delete_chapter(self, chapter: Chapter):
        self._delete_chapter(chapter)

    def user_delete_chapter(self, actor, chapter: Chapter):
        if self.chapter_policy.can_delete(actor, chapter):
            self.chapter_repo.delete_chapter(chapter)

        raise ChapterDeleteNotAllowed

    def user_get_chapter_context(
        self, 
        actor, 
        chapter: Chapter,
        include_translation = False,
        include_manga = False
    ):
        context = ChapterContextDTO(
            translation=None,
            manga=None
        )

        if include_manga:
            context.manga = chapter.translation.manga
        if include_translation:
            context.translation = chapter.translation

        return context

    def user_get_last_added_chapters(self, actor, cursor):
        return self.chapter_repo.get_last_added_chapters(actor, cursor)

    def user_get_translation_last_chapter_number(self, actor, translation_id):
        return self.chapter_repo.get_translation_last_chapter_number(translation_id)

class ChapterPublicService:

    def __init__(
        self,
        chapter_repo: ChapterRepository
    ):
        self.chapter_repo = chapter_repo

    def get_chapter_by_id(self, chapter_id) -> Chapter:
        chapter = self.chapter_repo.get_chapter_by_id(chapter_id, public=True)
        if chapter is None:
            raise ChapterNotFoundException()

        return chapter

class ChapterFrontendMetadataService(FrontendMetadataServiceMixin):
    
    def __init__(
        self,
        chapter_public_service: ChapterPublicService
    ):
        self.chapter_public_service = chapter_public_service

    def get(self, chapter_id: int):
        chapter = self.chapter_public_service.get_chapter_by_id(chapter_id)
        manga = chapter.manga

        metadata = FrontendMetadataDTO(
            title=f"Читать глава {chapter.chapter} {manga.name} | kanwoo",
            description="",
            canonical=f"https://kanwoo.ru/chapters/{chapter_id}",
            image=None,
            type=FrontentMetadataResouceTypeEnum.ARTICLE,
            indexable=True,
            published_at=chapter.created_at,
            modified_at=chapter.updated_at
        )

        return metadata


class ChapterContextService:

    def get(
        self, 
        actor, 
        chapter: Chapter,
        include_translation = False,
        include_manga = False
    ):
        context = ChapterContextDTO(
            translation=None,
            manga=None
        )

        if include_manga:
            context.manga = chapter.translation.manga
        if include_translation:
            context.translation = chapter.translation

        return context


class ChapterPagesOptimizationService:
    def __init__(
        self,
        storage: S3Storage | None,
        image_service_factory: ImageServiceFactory,
        chapter_repo: ChapterRepository,
    ):
        self.storage = storage
        self.image_service_factory = image_service_factory
        self.chapter_repo = chapter_repo

    def get_waiting_chapter_ids(self) -> list[int]:
        ### Получаетс список id всех глав, которые ожидают оптимизации ###
        if self.storage is None:
            return []
        return self.chapter_repo.get_waiting_optimization_ids()

    def enqueue_chapter(self, chapter_id: int) -> None:
        from .tasks import optimize_chapter_pages

        try:
            optimize_chapter_pages.delay(chapter_id)
        except OperationalError:
            current_app.logger.exception("Could not enqueue optimization for chapter %s", chapter_id)

    def optimize_page(self, page: ChapterPage) -> list[OptimizedPage]:
        return self.optimize_page_source(page.path)

    def optimize_page_source(self, path: str) -> list[OptimizedPage]:
        source = self.storage.read(path)

        return self.optimize_file(source)

    def optimize_file(
        self, source: File
    ) -> list[OptimizedPage]:
        image = self.image_service_factory.create(source, output_format="WEBP")
        
        size, boxes = self._get_part_regions(image.size)
        parts = image.encode_regions(size, boxes, "page.webp", "image/webp")
        
        return [
            self._save_part(part, index)
            for index, part in enumerate(parts)
        ]

    @staticmethod
    def _get_part_regions(
        original_size: tuple[int, int],
    ) -> tuple[tuple[int, int], Iterator[tuple[int, int, int, int]]]:
        original_width, original_height = original_size
        
        output_width = 1000
        output_height = max(
            1, 
            (original_height * output_width + original_width // 2) // original_width
        )
        
        part_count = (output_height + 1499) // 1500

        boxes = (
            (0, output_height * index // part_count, output_width, output_height * (index + 1) // part_count)
            for index in range(part_count)
        )

        return (output_width, output_height), boxes

    def _save_part(self, part: Img, order: int) -> OptimizedPage:
        """ Сохраняет изображение в хранилище файлов """
        
        page_uuid = UUIDGenerator.generate_uuid_v4()
        path = f"{OPTIMIZED_CHAPTER_OBJECT_PREFIX}{page_uuid}"

        self.storage.save(part.file, path)

        return OptimizedPage(
            file=FileModel(
                uuid=page_uuid,
                path=path,
                filename=None,
                mimetype=part.content_type,
                file_size=len(part.bytes),
            ),
            width=part.width,
            height=part.height,
            order=order,
        )
