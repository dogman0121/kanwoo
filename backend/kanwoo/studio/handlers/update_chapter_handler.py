from dependency_injector.wiring import Provide, inject
from flask import request
from marshmallow import ValidationError

from kanwoo import AppContainer, respond
from kanwoo.exceptions import ApiBadRequest
from kanwoo.idempotency.middleware import idempotent
from kanwoo.profile.middleware import profile_required
from kanwoo.studio.schemas import GetStudioChapterSchema, UpdateStudioChapterSchema
from kanwoo.studio.services import StudioChapterService


@profile_required()
@idempotent
@inject
def update_chapter_handler(
    current_profile,
    chapter_id,
    chapter_service: StudioChapterService = Provide[AppContainer.studio_chapter_service],
):
    try:
        data = UpdateStudioChapterSchema().load(request.get_json())
    except ValidationError as exc:
        raise ApiBadRequest(error="invalid_chapter", detail=exc.messages) from exc

    chapter = chapter_service.update_chapter(current_profile, chapter_id, data)
    return respond(data=GetStudioChapterSchema().dump(chapter))
