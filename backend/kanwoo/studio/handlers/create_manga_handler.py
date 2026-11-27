from flask import request
from dependency_injector.wiring import inject, Provide

from kanwoo.studio.services import StudioMangaService
from kanwoo import AppContainer
from kanwoo.utils import respond
from kanwoo.profile.middleware import profile_required
from kanwoo.profile.services import ProfileService
from kanwoo.manga.dto import CreateMangaDTO
from kanwoo.studio.schemas import CreateStudioMangaDataSchema, CreateStudioMangaFileSchema, GetStudioMangaSchema

@profile_required()
@inject
def create_manga_handler(
    current_profile,
    profile_slug,
    studio_service: StudioMangaService = Provide[AppContainer.studio_manga_service],
    profile_service: ProfileService = Provide[AppContainer.profile_container.profile_service]
):
    create_data_schema = CreateStudioMangaDataSchema().loads(request.form.get("data"))
    create_files_schema = CreateStudioMangaFileSchema().load({
        "poster": request.files.get("poster"),
        "backgound": request.files.get("background")
    })

    create_dto = CreateMangaDTO(
        name = create_data_schema.get("name"),
        description = create_data_schema.get("description"),
        type_id = create_data_schema.get("type_id"),
        status_id = create_data_schema.get("status_id"),
        adult_id = create_data_schema.get("adult_id"),
        year = create_data_schema.get("year"),
        genres_ids = create_data_schema.get("genres_ids"),
        privacy_id= create_data_schema.get("privacy_id"),
        poster = create_files_schema.get("poster"),
        background = create_files_schema.get("background"),
    )

    author = profile_service.user_get_profile_by_slug(current_profile, profile_slug)

    manga = studio_service.create_manga(current_profile, author, create_dto)

    manga_schema = GetStudioMangaSchema()

    return respond(data=manga_schema.dump(manga))