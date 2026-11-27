from flask import request
from dependency_injector.wiring import inject, Provide

from kanwoo.studio.services import StudioProfileService
from kanwoo import AppContainer, respond
from kanwoo.profile.middleware import profile_required
from kanwoo.profile.services import ProfileService
from kanwoo.profile.dto import UpdateProfileDTO
from kanwoo.profile.schemas import AvatarAction
from kanwoo.studio.schemas import UpdateStudioProfileDataSchema, UpdateStudioProfileFileSchema, GetStudioProfileSchema

@profile_required()
@inject
def update_profile_handler(
    current_profile,
    profile_slug,
    studio_service: StudioProfileService = Provide[AppContainer.studio_profile_service],
    profile_service: ProfileService = Provide[AppContainer.profile_container.profile_service]
):
    profile = profile_service.user_get_profile_by_slug(current_profile, profile_slug)

    update_data_schema = UpdateStudioProfileDataSchema().loads(request.form.get("data"))
    update_files_schema = UpdateStudioProfileFileSchema().load({
        "avatar": request.files.get("avatar")
    })                                      

    profile_update_dto = UpdateProfileDTO(
        name = update_data_schema.get("name"),
        slug = update_data_schema.get("slug"),
        about = update_data_schema.get("about"),
        links = update_data_schema.get("links"),
        avatar_action = update_data_schema.get("avatar")["action"],
        avatar = update_files_schema.get("avatar")
    )

    profile = studio_service.update_profile(current_profile, profile, profile_update_dto)

    return respond(data=GetStudioProfileSchema().dump(profile))