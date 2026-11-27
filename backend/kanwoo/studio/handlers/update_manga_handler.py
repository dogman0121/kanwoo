from flask import request
from dependency_injector.wiring import inject, Provide

from kanwoo.studio.services import StudioMangaService
from kanwoo import AppContainer
from kanwoo.utils import respond
from kanwoo.profile.middleware import profile_required
from kanwoo.manga.services import MangaService
from kanwoo.manga.dto import UpdateMangaDTO, NameTranslationDTO
from kanwoo.studio.schemas import GetStudioMangaSchema, UpdateStudioMangaDataSchema, UpdateStudioMangaFileSchema

@profile_required()
@inject
def update_manga_handler(
    current_profile,
    manga_slug,
    studio_service: StudioMangaService = Provide[AppContainer.studio_manga_service],
    manga_service: MangaService = Provide[AppContainer.manga_container.manga_service]
):
    manga = manga_service.user_get_manga_by_slug(current_profile, manga_slug)

    update_data_schema = UpdateStudioMangaDataSchema().loads(request.form.get("data"))
    update_files_schema = UpdateStudioMangaFileSchema().load({
        "poster": request.files.get("poster"),
        "background": request.files.get("background"),
        "promo_name": request.files.get("promo_name"),
        "promo_logo": request.files.get("promo_logo"),
        "promo_background": request.files.get("promo_background")
    })

    name_translations_prepared = [
        NameTranslationDTO(
            lang_id=translation.get('lang_id'),
            name=translation.get("name")
        )
        for translation in update_data_schema.get("name_translations")
    ]

    update_dto = UpdateMangaDTO(
        name = update_data_schema.get("name"),
        slug = update_data_schema.get("slug"),
        description = update_data_schema.get("description"),
        type_id = update_data_schema.get("type_id"),
        status_id = update_data_schema.get("status_id"),
        adult_id = update_data_schema.get("adult_id"),
        year = update_data_schema.get("year"),
        genres_ids = update_data_schema.get("genres_ids"),
        privacy_id= update_data_schema.get("privacy_id"),
        name_translations = name_translations_prepared,
        poster = update_files_schema.get("poster"),
        background = update_files_schema.get("background"),
        poster_action = update_data_schema.get("poster")["action"],
        background_action = update_data_schema.get("background")["action"],
        promo_name = update_files_schema.get("promo_name"),
        promo_logo = update_files_schema.get("promo_logo"),
        promo_background = update_files_schema.get("promo_background"),
        promo_name_action = update_data_schema.get("promo_name")["action"],
        promo_logo_action = update_data_schema.get("promo_logo")["action"],
        promo_background_action = update_data_schema.get("promo_background")["action"]
    )

    updated_manga = studio_service.update_manga(current_profile, manga, update_dto)

    return respond(data=GetStudioMangaSchema().dump(updated_manga))