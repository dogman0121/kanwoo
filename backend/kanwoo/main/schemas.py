from marshmallow import Schema, ValidationError, fields, validate
from kanwoo.file_storage import CHAPTER_OBJECT_PREFIX

from kanwoo.schemas import LanguageSchema, PrivacySchema
from kanwoo.manga.schemas import GetMangaGenreSchema, GetMangaAdultSchema, GetMangaStatusSchema, GetMangaTypeSchema


class MetaMainSchema(Schema):
    languages = fields.List(fields.Nested(LanguageSchema))
    privacies = fields.List(fields.Nested(PrivacySchema))

class MangaMetaSchema(Schema):
    genres = fields.List(fields.Nested(GetMangaGenreSchema))
    statuses = fields.List(fields.Nested(GetMangaStatusSchema))
    types = fields.List(fields.Nested(GetMangaTypeSchema))
    adults = fields.List(fields.Nested(GetMangaAdultSchema))

class MetaSchema(Schema):
    main = fields.Nested(MetaMainSchema)
    manga = fields.Nested(MangaMetaSchema)
    
class FeedbackCreateSchema(Schema):
    message = fields.String()


def validate_upload_token(token):
    if token.version != 4:
        raise ValidationError("Expected a UUID v4.")


UPLOAD_PREFIXES = {"chapter_page": CHAPTER_OBJECT_PREFIX}


class UploadFileSchema(Schema):
    uuid = fields.UUID(required=True, validate=validate_upload_token)
    file_type = fields.String(required=True, validate=validate.OneOf(UPLOAD_PREFIXES))
    mimetype = fields.String(required=True, validate=validate.OneOf(["image/jpeg", "image/png"]))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    file_size = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=20 * 1024 * 1024))
