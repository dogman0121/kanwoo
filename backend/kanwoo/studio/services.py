from functools import partial
from typing import List

from pytils.translit import slugify

from kanwoo.chapter.entity import ChapterPagesOptimizationStatus
from kanwoo.chapter.exceptions import ChapterNotFoundException, ChapterUpdateNotAllowed, ChapterWithNumberAlreadyExists
from kanwoo.chapter.models import Chapter, ChapterPage
from kanwoo.chapter.permissions import ChapterPolicy
from kanwoo.chapter.repositories import ChapterRepository
from kanwoo.chapter.services import ChapterPagesOptimizationService
from kanwoo.exceptions import ApiBadRequest, ApiException, ApiForbidden
from kanwoo.file_storage import CHAPTER_OBJECT_PREFIX, S3Storage
from kanwoo.database import DBTransaction
from kanwoo.entities import FileAction
from kanwoo.manga.dto import CreateMangaDTO, NameTranslationDTO, UpdateMangaDTO
from kanwoo.manga.exceptions import (
    MangaCreateNotAllowedException, MangaInvalidData, MangaNotFoundException, MangaUpdateNotAllowedException,
)
from kanwoo.manga.models import Manga, NameTranslation
from kanwoo.manga.permissions import MangaPolicy
from kanwoo.manga.repositories import MangaRepository
from kanwoo.manga.services import MangaMediaService
from kanwoo.moderation.dto import ModerationStatusUpdateDTO
from kanwoo.moderation.entity import ModerationStatus
from kanwoo.moderation.services import ModerationService
from kanwoo.models import FileModel
from kanwoo.profile.dto import CreateProfileDTO, UpdateProfileDTO
from kanwoo.profile.exceptions import ProfileUpdateNotAllowedException
from kanwoo.profile.models import Profile, ProfileLink
from kanwoo.profile.permissions import ProfilePolicy
from kanwoo.profile.repositories import ProfileRepository
from kanwoo.profile.schemas import AvatarAction
from kanwoo.profile.services import ProfileAvatarService
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
    def __init__(
        self,
        manga_media_service: MangaMediaService,
        manga_repo: MangaRepository,
        manga_policy: MangaPolicy,
        moderation_service: ModerationService,
        db_transaction: DBTransaction,
    ):
        self.manga_media_service = manga_media_service
        self.manga_repo = manga_repo
        self.manga_policy = manga_policy
        self.moderation_service = moderation_service
        self.db_transaction = db_transaction

    def _get_slug(self, name: str):
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while self.manga_repo.get_manga_by_slug_from_system(slug):
            slug = f"{base_slug}{suffix}"
            suffix += 1
        return slug

    def _prepare_name_translations(self, manga: Manga, name_translations: List[NameTranslationDTO]):
        return [
            NameTranslation(
                manga_id=manga.id,
                lang_id=translation.lang_id,
                name=translation.name
            ) for translation in name_translations
        ]

    def create_manga(self, creator_profile, author_profile, data: CreateMangaDTO):
        if not self.manga_policy.can_create(creator_profile, author_profile):
            raise MangaCreateNotAllowedException()

        if not self.manga_repo.check_if_genres_exists(data.genres_ids):
            raise MangaNotFoundException()

        if data.slug:
            slug = self._get_slug(data.slug)
        else:
            slug = self._get_slug(data.name)

        genres = self.manga_repo.get_genres_by_ids(data.genres_ids)

        manga = Manga(
            slug=slug,
            name=data.name,
            description=data.description,
            type_id=data.type_id,
            status_id=data.status_id,
            year=data.year,
            adult_id=data.adult_id,
            genres=genres,
            author_id= author_profile.id if author_profile else None,
            creator_id=creator_profile.id,
            privacy_id=data.privacy_id
        )

        with self.db_transaction:
            if data.poster:
                self.manga_media_service.set_poster(manga, data.poster)
            if data.background:
                self.manga_media_service.set_background(manga, data.background)
            if data.promo_name:
                self.manga_media_service.set_promo_name(manga, data.promo_name)
            if data.promo_logo:
                self.manga_media_service.set_promo_logo(manga, data.promo_logo)
            if data.promo_background:
                self.manga_media_service.set_promo_background(manga, data.promo_background)

            manga = self.manga_repo.create_manga(manga)

        moderation_status_dto = ModerationStatusUpdateDTO(
            status_type_id=ModerationStatus.MODERATION.value,
            message="Init status"
        )

        self.moderation_service.system_update_manga_moderation_status(manga, moderation_status_dto)

        return manga

    def update_manga(self, profile, manga: Manga, data: UpdateMangaDTO):
        if not self.manga_policy.can_edit(profile, manga):
            raise MangaUpdateNotAllowedException

        slug = slugify(data.slug)
        if slug and manga.slug != slug and self.manga_repo.get_manga_by_slug_from_system(slug):
            raise MangaInvalidData(detail={"slug": ["Invalid slug."]})

        name_translations = self._prepare_name_translations(manga, data.name_translations)

        genres = self.manga_repo.get_genres_by_ids(data.genres_ids)

        with self.db_transaction:
            self.manga_repo.update_manga(manga, {
                "name": data.name,
                "name_translations": name_translations,
                "slug": slug,
                "description": data.description,
                "type_id": data.type_id,
                "status_id": data.status_id,
                "adult_id": data.adult_id,
                "year": data.year,
                "genres": genres,
                "privacy_id": data.privacy_id
            })

            if data.poster_action != FileAction.KEEP:
                self.manga_media_service.update_poster(manga, data.poster)
            if data.background_action != FileAction.KEEP:
                self.manga_media_service.update_background(manga, data.background)
            if data.promo_name_action != FileAction.KEEP:
                self.manga_media_service.update_promo_name(manga, data.promo_name)
            if data.promo_logo_action != FileAction.KEEP:
                self.manga_media_service.update_promo_logo(manga, data.promo_logo)
            if data.promo_background_action != FileAction.KEEP:
                self.manga_media_service.update_promo_background(manga, data.promo_background)

        return manga


class StudioProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        profile_avatar_service: ProfileAvatarService,
        profile_policy: ProfilePolicy,
        db_transaction: DBTransaction,
    ):
        self.profile_repo = profile_repo
        self.profile_avatar_service = profile_avatar_service
        self.profile_policy = profile_policy
        self.db_transaction = db_transaction

    def _get_slug(self, name: str):
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while self.profile_repo.system_get_profile_by_slug(slug):
            slug = f"{base_slug}{suffix}"
            suffix += 1
        return slug

    def create_profile(self, profile, profile_dto: CreateProfileDTO):
        with self.db_transaction:
            profile = Profile(
                name=profile_dto.name,
                slug=self._get_slug(profile_dto.slug),
                about=profile_dto.about,
                creator_id=profile_dto.creator_id,
                owner_id=profile_dto.owner_id,
            )

            if profile_dto.avatar:
                self.profile_avatar_service.update_profile_avatar(profile, profile_dto.avatar)

            self.profile_repo.create_profile(profile)

            return profile

    def update_profile(self, current_profile, profile: Profile, data: UpdateProfileDTO):
        if not self.profile_policy.can_edit(current_profile, profile):
            raise ProfileUpdateNotAllowedException

        if data.links:
            links = [
                ProfileLink(
                    name=l.get("name"),
                    link=l.get("link")
                ) for l in data.links
            ]
        else:
            links = []

        with self.db_transaction:
            if data.avatar_action == FileAction.DELETE:
                self.profile_avatar_service.delete_profile_avatar(profile)
            elif data.avatar_action == FileAction.UPDATE:
                self.profile_avatar_service.update_profile_avatar(profile, data.avatar)

            profile.update({
                "name": data.name,
                "slug": data.slug,
                "about": data.about,
                "links": links,
            })

        return profile
