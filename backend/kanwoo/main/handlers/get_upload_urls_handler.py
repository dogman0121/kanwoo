from dependency_injector.wiring import Provide, inject
from flask import request
from marshmallow import ValidationError
from sqlalchemy.dialects.postgresql import insert

from kanwoo import AppContainer, respond
from kanwoo.exceptions import ApiBadRequest, ApiException, ApiForbidden
from kanwoo.file_storage import S3Storage
from kanwoo.main.schemas import UPLOAD_PREFIXES, UploadFileSchema
from kanwoo.models import FileModel
from kanwoo.profile.middleware import profile_required
from kanwoo.unit_of_work import UnitOfWork


@profile_required()
@inject
def get_upload_urls_handler(
    current_profile,
    storage: S3Storage | None = Provide[AppContainer.object_storage],
    uow: UnitOfWork = Provide[AppContainer.unit_of_work],
):
    try:
        uploads = UploadFileSchema(many=True).load(request.get_json())
    except ValidationError as exc:
        raise ApiBadRequest(error="invalid_upload_metadata", detail=exc.messages) from exc

    if not 1 <= len(uploads) <= 100:
        raise ApiBadRequest(error="invalid_upload_count")

    if storage is None:
        raise ApiException(error="upload_storage_unavailable", status_code=503)

    response = []
    with uow:
        for upload in uploads:
            token = str(upload["uuid"])
            key = f"{UPLOAD_PREFIXES[upload['file_type']]}{token}"
            metadata = {
                "uploaded_by_profile_id": current_profile.id,
                "filename": upload["name"],
                "mimetype": upload["mimetype"],
                "file_size": upload["file_size"],
            }
            uow.db_session.execute(
                insert(FileModel).values(uuid=token, path=key, **metadata)
                .on_conflict_do_nothing(index_elements=[FileModel.uuid])
            )
            record = uow.db_session.get(FileModel, token)
            if record.uploaded_by_profile_id != current_profile.id:
                raise ApiForbidden()
            if (
                record.path != key
                or record.is_deleted
                or any(getattr(record, name) != value for name, value in metadata.items())
            ):
                raise ApiBadRequest(error="upload_metadata_does_not_match", status_code=409)

            signed = storage.get_upload_url(
                record.path, content_type=record.mimetype, size=record.file_size
            )
            response.append({"uuid": token, "presigned_url": signed})
    return respond(data=response)
