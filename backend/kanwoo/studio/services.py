from kanwoo.chapter.exceptions import ChapterWithNumberAlreadyExists
from kanwoo.chapter.models import Chapter, Page
from kanwoo.chapter.repositories import ChapterRepository
from kanwoo.exceptions import ApiNotFound
from kanwoo.file_storage import FileStorageMixin
from kanwoo.translation.models import Translation
from kanwoo.unit_of_work import UnitOfWork
from kanwoo.uuid import UUIDGenerator

from .dto import CreateStudioChapterDTO

class StudioChapterService():
    pass

class StudioTranslationService:

    def __init__(
        self,
        chapter_repo: ChapterRepository,
        file_storage: FileStorageMixin,
        unit_of_work: UnitOfWork,
    ):
        self.unit_of_work = unit_of_work
        self.chapter_repo = chapter_repo
        self.file_storage = file_storage

    def create_chapter(
        self, translation: Translation, create_chapter_data: CreateStudioChapterDTO
    ) -> Chapter:
        data = create_chapter_data
        if self.chapter_repo.check_chapter_with_number(
            translation.id, data.chapter, data.extra_number
        ):
            raise ChapterWithNumberAlreadyExists()

        for page in data.pages:
            if not self.file_storage.exists(page.key):
                raise ApiNotFound(detail={"key": page.key}, error="chapter_page_not_found")

        chapter = Chapter(
            translation_id=translation.id,
            creator_id=data.creator_id,
            chapter=data.chapter,
            privacy_id=data.privacy_id,
            name=data.name,
            extra_number=data.extra_number,
            pages=[
                Page(
                    uuid=UUIDGenerator.generate_uuid_v4(),
                    path=page.key,
                    orig_filename=page.original_filename,
                    width=page.width,
                    height=page.height,
                    order=order,
                )
                for order, page in enumerate(data.pages)
            ],
        )
        with self.unit_of_work:
            return self.chapter_repo.create_chapter(chapter)

class StudioMangaService:
    pass


class StudioProfileService:
    pass
