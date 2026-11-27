from functools import partial

from kanwoo.chapter.entity import ChapterPagesOptimizationStatus
from kanwoo.chapter.exceptions import ChapterNotFoundException, ChapterUpdateNotAllowed, ChapterWithNumberAlreadyExists
from kanwoo.chapter.models import Chapter, ChapterPage
from kanwoo.chapter.permissions import ChapterPolicy
from kanwoo.chapter.repositories import ChapterRepository
from kanwoo.chapter.services import ChapterPagesOptimizationService
from kanwoo.exceptions import ApiBadRequest, ApiException, ApiForbidden
from kanwoo.file_storage import CHAPTER_OBJECT_PREFIX, S3Storage
from kanwoo.models import FileModel
from kanwoo.translation.services import TranslationService
from kanwoo.unit_of_work import UnitOfWork

from .dto import ChapterPageDTO, CreateStudioChapterDTO, UpdateStudioChapterDTO


class StudioChapterService:
    def __init__(
        self,
        chapter_repo: ChapterRepository,
        chapter_policy: ChapterPolicy,
        unit_of_work: UnitOfWork,
        storage: S3Storage | None,
        translation_service: TranslationService,
        optimization_service: ChapterPagesOptimizationService,
    ):
        self.chapter_repo = chapter_repo
        self.chapter_policy = chapter_policy
        self.unit_of_work = unit_of_work
        self.storage = storage
        self.translation_service = translation_service
        self.optimization_service = optimization_service

    def create_chapter(self, profile, translation_id: int, data: CreateStudioChapterDTO) -> Chapter:
        translation = self.translation_service.user_get_translation_by_id(profile, translation_id)
        if not self.translation_service.translation_policy.can_edit(profile, translation):
            raise ApiForbidden()

        chapter = Chapter(
            translation_id=translation.id,
            creator_id=profile.id,
            chapter=data.chapter,
            privacy_id=data.privacy_id,
            name=data.name,
            extra_number=data.extra_number,
            optimization_status_id=ChapterPagesOptimizationStatus.WAITING.value,
            chapter_pages=[
                ChapterPage(
                    file=self._get_uploaded_file(page.uuid),
                    width=page.width,
                    height=page.height,
                    order=order,
                    is_orig=True,
                    process_status_id=ChapterPagesOptimizationStatus.WAITING.value,
                )
                for order, page in enumerate(data.pages)
            ],
        )
        with self.unit_of_work:
            self.chapter_repo.create_chapter(chapter)
            self.unit_of_work.after_commit(partial(self.optimization_service.enqueue_chapter, chapter.id))
        return chapter

    def update_chapter(self, profile, chapter_id: int, data: UpdateStudioChapterDTO) -> Chapter:
        chapter = self.chapter_repo.get_chapter_by_id(chapter_id, public=False, for_update=True)
        if chapter is None:
            raise ChapterNotFoundException()
        if not self.chapter_policy.can_edit(profile, chapter):
            raise ChapterUpdateNotAllowed()
        
        with self.unit_of_work:
            number = data.chapter, data.extra_number
            if number != (chapter.chapter, chapter.extra_number) and self.chapter_repo.check_chapter_with_number(
                chapter.translation_id, *number
            ):
                raise ChapterWithNumberAlreadyExists()

            has_new_pages = self._update_pages(chapter, data.pages)
            chapter.update({
                "name": data.name,
                "chapter": number[0],
                "extra_number": number[1],
                "privacy_id": data.privacy_id,
            })
            self.chapter_repo.flush_chapter()
            if has_new_pages:
                chapter.optimization_status_id = ChapterPagesOptimizationStatus.WAITING.value
                self.unit_of_work.after_commit(partial(self.optimization_service.enqueue_chapter, chapter_id))
            return chapter

    def _update_pages(self, chapter: Chapter, pages: list[ChapterPageDTO]) -> bool:
        existing_pages_dict = {page.uuid: page for page in chapter.chapter_pages}
        has_new_pages = False

        updated_pages = []
        for order, page_from_form in enumerate(pages):
            is_new_page_exists = page_from_form.is_new and page_from_form.uuid in existing_pages_dict
            is_old_page_not_exists = not page_from_form.is_new and page_from_form.uuid not in existing_pages_dict
            if is_new_page_exists or is_old_page_not_exists:
                raise ApiBadRequest(error="invalid_chapter_page", detail={"uuid": page_from_form.uuid})

            if page_from_form.is_new:
                page = ChapterPage(
                    file=self._get_uploaded_file(page_from_form.uuid),
                    width=page_from_form.width,
                    height=page_from_form.height,
                    is_orig=True,
                    process_status_id=ChapterPagesOptimizationStatus.WAITING.value,
                )
                has_new_pages = True
            else:
                page = existing_pages_dict[page_from_form.uuid]

            page.order = order
            updated_pages.append(page)

        chapter.chapter_pages = updated_pages
        return has_new_pages

    def _get_uploaded_file(self, token: str) -> FileModel:
        if self.storage is None:
            raise ApiException(error="upload_storage_unavailable", status_code=503)

        upload = FileModel.get(token)
        if (
            upload is None
            or upload.is_deleted
            or upload.path != f"{CHAPTER_OBJECT_PREFIX}{token}"
            or not self.storage.exists(upload.path)
        ):
            raise ApiBadRequest(error="chapter_page_not_uploaded", detail={"uuid": token})
        return upload


class StudioMangaService:
    pass


class StudioProfileService:
    pass
