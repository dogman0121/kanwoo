from datetime import datetime
from typing import Optional, Tuple, List

from kanwoo.frontend_metadata import FrontendMetadataDTO, FrontentMetadataResouceTypeEnum
from kanwoo.profile.entity import AnonymousProfile
from kanwoo.frontend_metadata import FrontendMetadataServiceMixin
from kanwoo.file_storage import FileStorageMixin
from kanwoo.database import DBTransaction
from kanwoo.uuid import UUIDGenerator
from kanwoo.image import ImageServiceFactory
from kanwoo.models import FileModel
from kanwoo.entities import File
from kanwoo.profile.entity import AnonymousProfile
from kanwoo.collection.services import CollectionService

from .models import ( 
    Manga, 
    Poster, 
    PosterFile, 
    Background, 
    PromoName, 
    PromoLogo, 
    PromoBackground,
    MangaSuggestion
)
from .dto import (
    MangaSuggestionCreateDTO, 
    MangaContextDTO, 
    MangaViewerContextDTO,
    MangaStatDTO
)
from .repositories import (
    MangaRepository, 
    MangaSuggestionRepository, 
    MangaStatsRepository,
    MangaStatRepository
)
from .exceptions import MangaNotFoundException, MangaDeleteNotAllowedException
from .permissions import MangaPolicy


class MangaMediaService:
    """ Service for work with manga media files. Don't check permissions! """

    POSTER_SIZES = {
        "thumbnail": (80, 120),
        "small": (200, 300),
        "medium": (400, 600),
        "large": (600, 900),
    }
    BACKGROUND_SIZE = (1920, 1080)
    PROMO_NAME_SIZE = (420, 360)
    PROMO_LOGO_SIZE = (540, 435)
    PROMO_BACKGROUND_SIZE = (1160, 580)

    def __init__(self, file_storage: FileStorageMixin, image_service_factory: ImageServiceFactory, manga_repo: MangaRepository):
        self.image_service_factory = image_service_factory
        self.manga_repo = manga_repo
        self.file_storage = file_storage

    def _save_image(self, image_service, size: Tuple, extension: str, filename: str) -> FileModel:
        file_uuid = UUIDGenerator.generate_uuid_v4()
        path = f"manga/{file_uuid}{extension}"
        image = image_service.resize(size)
        self.file_storage.save(image, path)
        return FileModel(
            uuid=file_uuid,
            path=path,
            filename=filename,
            mimetype=image.content_type,
            file_size=len(image.bytes),
        )

    def set_poster(self, manga: Manga, poster_file: File):
        poster_uuid = UUIDGenerator.generate_uuid_v4()
        poster = Poster(
            uuid=poster_uuid
        )

        image_service = self.image_service_factory.create(poster_file, "JPEG")

        for quality, size in self.POSTER_SIZES.items():
            file = self._save_image(image_service, size, ".jpg", poster_file.filename)

            poster_version = PosterFile(
                uuid=file.uuid,
                file=file,
                poster_uuid=poster_uuid,
                type=quality,
            )

            poster.files.append(poster_version)
                
        
        self.manga_repo.set_poster(manga, poster)

    def set_background(self, manga, background_file: File):
        image_service = self.image_service_factory.create(background_file, "JPEG")

        file = self._save_image(image_service, self.BACKGROUND_SIZE, ".jpg", background_file.filename)
        background = Background(uuid=file.uuid, file=file)

        self.manga_repo.set_background(manga, background)

        return file.uuid

    def set_promo_name(self, manga, promo_name_file: File):
        image_service = self.image_service_factory.create(promo_name_file, "WEBP")

        file = self._save_image(image_service, self.PROMO_NAME_SIZE, ".webp", promo_name_file.filename)
        promo_name = PromoName(uuid=file.uuid, file=file)

        self.manga_repo.set_promo_name(manga, promo_name)

    def set_promo_logo(self, manga, promo_logo_file: File):
        image_service = self.image_service_factory.create(promo_logo_file, "WEBP")

        file = self._save_image(image_service, self.PROMO_LOGO_SIZE, ".webp", promo_logo_file.filename)
        promo_logo = PromoLogo(uuid=file.uuid, file=file)

        self.manga_repo.set_promo_logo(manga, promo_logo)

    def set_promo_background(self, manga, promo_background_file: File):
        image_service = self.image_service_factory.create(promo_background_file, "WEBP")

        file = self._save_image(image_service, self.PROMO_BACKGROUND_SIZE, ".webp", promo_background_file.filename)
        promo_background = PromoBackground(uuid=file.uuid, file=file)

        self.manga_repo.set_promo_background(manga, promo_background)

    def delete_poster(self, manga):
        self.manga_repo.delete_poster(manga)

    def delete_background(self, manga):
        self.manga_repo.delete_background(manga)

    def delete_promo_name(self, manga):
        self.manga_repo.delete_promo_name(manga)

    def delete_promo_logo(self, manga):
        self.manga_repo.delete_promo_logo(manga)

    def delete_promo_background(self, manga):
        self.manga_repo.delete_promo_background(manga)

    def update_poster(self, manga, poster_file: Optional[File]):
        if poster_file:
            self.set_poster(manga, poster_file)
        else:
            self.delete_poster(manga)
    
    def update_background(self, manga, background_file: Optional[File]):
        if background_file:
            self.set_background(manga, background_file)
        else:
            self.delete_background(manga)

    def update_promo_name(self, manga, promo_name_file: Optional[File]):
        if promo_name_file:
            self.set_promo_name(manga, promo_name_file)
        else:
            self.delete_promo_name(manga)

    def update_promo_logo(self, manga, promo_logo_file: Optional[File]):
        if promo_logo_file:
            self.set_promo_logo(manga, promo_logo_file)
        else:
            self.delete_promo_logo(manga)

    def update_promo_background(self, manga, promo_background_file: Optional[File]):
        if promo_background_file:
            self.set_promo_background(manga, promo_background_file)
        else:
            self.delete_promo_background(manga)

class MangaService:

    def __init__(
        self, 
        manga_repo: MangaRepository,
        manga_policy: MangaPolicy,
        collection_service: CollectionService,
        db_transaction: DBTransaction
    ):
        self.manga_repo = manga_repo
        self.manga_policy = manga_policy
        self.collection_service = collection_service
        self.db_transaction = db_transaction

    def user_get_manga_by_id(self, profile, manga_id):
        if isinstance(profile, AnonymousProfile):
            manga = self.manga_repo.get_manga_by_id_from_user(None, manga_id)
        else:
            manga = self.manga_repo.get_manga_by_id_from_user(profile, manga_id)

        if manga is None:
            raise MangaNotFoundException

        return manga
    
    def user_get_manga_by_slug(self, profile, slug, by_link=False):
        
        manga = self.manga_repo.get_manga_by_slug_from_user(profile, slug, by_link=by_link)

        if manga is None:
            raise MangaNotFoundException()

        return manga
    
    def system_get_manga_by_slug(self, slug):
        manga = self.manga_repo.get_manga_by_slug_from_system(slug)

        if manga is None:
            raise MangaNotFoundException

        return manga
    
    def _delete_manga(self, manga: Manga):
        self.manga_repo.delete_manga(manga)

    def system_delete_manga(self, manga: Manga):
        self._delete_manga(manga)

    def user_delete_manga(self, profile, manga: Manga):
        if self.manga_policy.can_delete(profile, manga):
            self._delete_manga(manga)
        
        raise MangaDeleteNotAllowedException

    def user_get_profile_manga(self, actor, profile):
        return self.manga_repo.get_profile_manga(actor, profile.id)

    def user_get_manga_edit_form(self, profile, manga: Manga):
        """ Returns edit form data and blocked fields """
        
        return manga, []

    def user_add_manga_view(self, manga, profile):
        with self.db_transaction:
            manga.update({
                "views": manga.views + 1
            })

    def user_get_manga_context(self, actor, manga):
        context = MangaContextDTO(
            viewer=None
        )

        if not isinstance(actor, AnonymousProfile):
            collections = self.collection_service.user_get_collections_with_manga(actor, manga.id)
            context.viewer = MangaViewerContextDTO(
                collections=[c.id for c in collections]
            )
        return context

class MangaSuggestionService:

    def __init__(self, manga_suggestion_repo: MangaSuggestionRepository):
        self.manga_suggestion_repo = manga_suggestion_repo

    def user_create_suggestion(self, profile, data: MangaSuggestionCreateDTO):
        suggestion = MangaSuggestion(
            name=data.name,
            link=data.link,
            comment=data.comment,
            creator_id=data.creator_id
        )

        suggestion.add(commit=True)
        
        return self.manga_suggestion_repo.create_suggestion(suggestion)
        
    def user_get_suggestion_by_id(self, profile, suggestion_id):
        return self.manga_suggestion_repo.get_suggestion_by_id(suggestion_id)

    def user_get_suggestions(self, profile, resolved=None):
        return self.manga_suggestion_repo.get_suggestions(resolved=resolved)

    def user_resolve_suggestion(self, profile, suggestion):
        return self.manga_suggestion_repo.update_suggestion(suggestion, {"resolved_at": datetime.now()})
    
    def user_get_unresolved_suggestions_count(self, profile):
        return self.manga_suggestion_repo.get_active_suggestions_count()

class MangaStatsService:
    def __init__(
        self, 
        manga_stats_repo: MangaStatsRepository
    ):
        self.manga_stats_repo = manga_stats_repo

    def user_get_most_viewed_manga(self):
        return self.manga_stats_repo.get_most_viewed_manga()

    def user_get_ended_manga(self):
        return self.manga_stats_repo.get_ended_manga()

    def user_get_newest_manga(self):
        return self.manga_stats_repo.get_newest_manga()

    def user_get_manga_with_promo(self):
        return self.manga_stats_repo.get_manga_with_promo()


class MangaStatService:

    def __init__(
        self,
        manga_stat_repo: MangaStatRepository,
        db_transaction: DBTransaction
    ):
        self.manga_stat_repo = manga_stat_repo
        self.db_transaction = db_transaction

    def get(self, manga_slug: str):
        views_count = self.manga_stat_repo.get_views(manga_slug)
        comment_count = self.manga_stat_repo.get_comments(manga_slug)
        saves_count = self.manga_stat_repo.get_saves(manga_slug)

        return MangaStatDTO(
            views=views_count or 0,
            comments=comment_count or 0,
            saves=saves_count or 0
        )

    def add_view(self, manga_slug: str):
        with self.db_transaction:
            self.manga_stat_repo.add_view(manga_slug)
        

class MangaContextService:

    def __init__(
        self,
        collection_service: CollectionService
    ):
        self.collection_service = collection_service

    def get(self, actor, manga):
        context = MangaContextDTO(
            viewer=None
        )

        if not isinstance(actor, AnonymousProfile):
            collections = self.collection_service.user_get_collections_with_manga(actor, manga.id)
            context.viewer = MangaViewerContextDTO(
                collections=[c.id for c in collections]
            )
        return context

class MangaPublicService:

    def __init__(
        self,
        manga_repo: MangaRepository
    ):
        self.manga_repo = manga_repo

    def get_manga_by_slug(self, slug: str):
        manga = self.manga_repo.get_manga_by_slug(slug, public=True)

        if manga is None:
            raise MangaNotFoundException()

        return manga
        

class MangaFrontendMetadataService(FrontendMetadataServiceMixin):

    def __init__(
        self,
        manga_public_service: MangaPublicService
    ):
        self.manga_public_service = manga_public_service

    def get(self, slug: str):
        manga = self.manga_public_service.get_manga_by_slug(slug)

        metadata = FrontendMetadataDTO(
            title=f"{manga.name} | kanwoo",
            description=manga.description,
            canonical=f"https://kanwoo.ru/manga/{slug}",
            image=None,
            type=FrontentMetadataResouceTypeEnum.BOOK,
            indexable=True,
            published_at=manga.created_at,
            modified_at=manga.updated_at
        )

        if manga.poster:
            metadata.image = str(manga.poster.medium)

        return metadata