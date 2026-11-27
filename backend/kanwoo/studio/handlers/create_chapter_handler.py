from dependency_injector.wiring import Provide, inject
from flask import request
from marshmallow import ValidationError

from kanwoo import AppContainer, respond
from kanwoo.exceptions import ApiBadRequest
from kanwoo.idempotency.middleware import idempotent
from kanwoo.profile.middleware import profile_required
from kanwoo.studio.schemas import CreateStudioChapterSchema, GetStudioChapterSchema
from kanwoo.studio.services import StudioChapterService


@profile_required()
@idempotent
@inject
def create_chapter_handler(
    current_profile,
    translation_id,
    chapter_service: StudioChapterService = Provide[AppContainer.studio_chapter_service],
):
    data = CreateStudioChapterSchema().load(request.json)

    chapter = chapter_service.create_chapter(current_profile, translation_id, data)

    return respond(data=GetStudioChapterSchema().dump(chapter))
