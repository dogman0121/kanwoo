from marshmallow import fields, post_load, Schema, validate, validates_schema, ValidationError
from enum import Enum

from .dto import ChapterPageDTO, CreateStudioChapterDTO, UpdateStudioChapterDTO

from kanwoo.schemas import Json, File
from kanwoo.main.schemas import validate_upload_token
from kanwoo.entities import FileAction
from kanwoo.manga.schemas import (
    GetMangaSchemaFull,
    MANGA_POSTER_ALLOWED_EXTENSIONS,
    MANGA_POSTER_ALLOWED_TYPES,
    MANGA_POSTER_MAX_SIZE,
    MANGA_BACKGROUND_ALLOWED_EXTENSIONS,
    MANGA_BACKGROUND_ALLOWED_TYPES,
    MANGA_BACKGROUND_MAX_SIZE,
    MANGA_PROMO_BACKGROUND_ALLOWED_EXTENSIONS,
    MANGA_PROMO_BACKGROUND_ALLOWED_TYPES,
    MANGA_PROMO_BACKGROUND_MAX_SIZE,
    MANGA_PROMO_LOGO_ALLOWED_EXTENSIONS,
    MANGA_PROMO_LOGO_ALLOWED_TYPES,
    MANGA_PROMO_LOGO_MAX_SIZE,
    MANGA_PROMO_NAME_ALLOWED_EXTENSIONS,
    MANGA_PROMO_NAME_ALLOWED_TYPES,
    MANGA_PROMO_NAME_MAX_SIZE
)
from kanwoo.translation.schemas import GetTranslationSchemaFull
from kanwoo.moderation.schemas import ModerationStatusTypeSchema
from kanwoo.chapter.schemas import GetChapterSchemaFull, GetPageSchema
from kanwoo.translation.entities import ReadingModeEnum
from kanwoo.profile.schemas import (
    AvatarAction,
    PROFILE_AVATAR_ALLOWED_EXTENSIONS,
    PROFILE_AVATAR_ALLOWED_TYPES,
    PROFILE_AVATAR_MAX_SIZE,
    GetProfileSchema,
    GetProfilePermissionsSchema
)

class GetModerationStatusSchema(Schema):
    id = fields.Integer()
    status_type = fields.Nested(ModerationStatusTypeSchema)
    message = fields.String()
    created_at = fields.String()
    
class GetStudioMangaSchema(GetMangaSchemaFull):
    moderation_status = fields.Nested(GetModerationStatusSchema)

class GetStudioMangaInfoFormSchema(Schema):
    slug = fields.String(required=True)
    name = fields.String(required=True)
    poster = fields.Nested("GetMangaPosterSchema")
    status = fields.Nested("GetMangaStatusSchema")
    type = fields.Nested("GetMangaTypeSchema")
    adult = fields.Nested("GetMangaAdultSchema")
    year = fields.Integer()
    name_translations = fields.List(fields.Nested("GetMangaNameTranslationsSchema"))
    description = fields.String()
    genres = fields.List(fields.Nested("GetMangaGenreSchema"))
    background = fields.String()
    promo_name = fields.String()
    promo_logo = fields.String()
    promo_background = fields.String()
    author = fields.Nested("GetProfileSchema")
    privacy = fields.Nested("PrivacySchema")

    blocked_fields = fields.Method("get_blocked_fields")

    def get_blocked_fields(self, obj):
        return self.context.get("blocked_fields", [])


class GetStudioTranslationSchema(GetTranslationSchemaFull):
    name = fields.String()

class UpdateStudioTranslationSchema(Schema):
    name = fields.String()
    privacy_id = fields.Integer()
    default_reading_mode_id = fields.Enum(ReadingModeEnum, by_value=True)

class CreateStudioProfileTranslationSchema(Schema):
    manga_id = fields.Integer()
    lang_id = fields.Integer()
    name = fields.String()
    privacy_id = fields.Integer()

class CreateStudioMangaTranslationSchema(Schema):
    lang_id = fields.Integer()
    name = fields.String()
    privacy_id = fields.Integer()

class GetStudioChapterListItemSchema(GetChapterSchemaFull):
    class Meta:
        fields = ("id", "name", "chapter", "extra_number", "privacy")

    extra_number = fields.Integer(allow_none=True)


class GetStudioChapterSchema(GetChapterSchemaFull):
    extra_number = fields.Integer(allow_none=True)
    pages = fields.List(fields.Nested(GetPageSchema), attribute="chapter_pages")
    pages_count = fields.Function(lambda chapter: len(chapter.chapter_pages))

class UploadedChapterPageSchema(Schema):
    uuid = fields.UUID(required=True, validate=validate_upload_token)
    width = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=100_000))
    height = fields.Integer(required=True, strict=True, validate=validate.Range(min=1, max=100_000))

    @post_load
    def to_dto(self, data, **kwargs):
        return ChapterPageDTO(uuid=str(data["uuid"]), is_new=True, width=data["width"], height=data["height"])


class StudioChapterDetailsSchema(Schema):
    name = fields.String(allow_none=True)
    chapter = fields.Integer(required=True, strict=True)
    privacy_id = fields.Integer(required=True, strict=True, validate=validate.OneOf([1, 2, 3]))
    extra_number = fields.Integer(allow_none=True, strict=True)


def validate_unique_page_uuids(pages: list[ChapterPageDTO]) -> None:
    if len({page.uuid for page in pages}) != len(pages):
        raise ValidationError("Page UUIDs must be unique.")


class CreateStudioChapterSchema(StudioChapterDetailsSchema):
    pages = fields.List(
        fields.Nested(UploadedChapterPageSchema),
        required=True,
        validate=[validate.Length(min=1), validate_unique_page_uuids],
    )

    @post_load
    def to_dto(self, data, **kwargs):
        return CreateStudioChapterDTO(**data)


class UpdateStudioChapterPageSchema(UploadedChapterPageSchema):
    is_new = fields.Boolean(required=True)
    width = fields.Integer(strict=True, validate=validate.Range(min=1, max=100_000))
    height = fields.Integer(strict=True, validate=validate.Range(min=1, max=100_000))

    @validates_schema
    def validate_dimensions(self, data, **kwargs):
        errors = {}
        for field in ("width", "height"):
            if data["is_new"] and field not in data:
                errors[field] = ["Missing data for new page."]
            elif not data["is_new"] and field in data:
                errors[field] = ["Dimensions are only accepted for new pages."]
        if errors:
            raise ValidationError(errors)

    @post_load
    def to_dto(self, data, **kwargs):
        return ChapterPageDTO(
            uuid=str(data["uuid"]), is_new=data["is_new"], width=data.get("width"), height=data.get("height"),
        )


class UpdateStudioChapterSchema(StudioChapterDetailsSchema):
    pages = fields.List(
        fields.Nested(UpdateStudioChapterPageSchema),
        required=True,
        validate=validate_unique_page_uuids,
    )

    @post_load
    def to_dto(self, data, **kwargs):
        return UpdateStudioChapterDTO(**data)

class CreateUpdateNameTranslationSchema(Schema):
    lang = fields.String()
    name = fields.String()

class CreateStudioMangaSchema(Schema):
    name = fields.String()
    name_translations = Json(fields.Nested(CreateUpdateNameTranslationSchema), allow_none=True)
    description = fields.String(allow_none=True)
    status_id = fields.Integer()
    type_id = fields.Integer()
    adult_id = fields.Integer()
    genres_ids = fields.List(fields.Integer())
    year = fields.Integer()
    privacy_id = fields.Integer()
    background = File(
        max_file_size=MANGA_BACKGROUND_MAX_SIZE, 
        allowed_file_types=MANGA_BACKGROUND_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_BACKGROUND_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    poster = File(
        max_file_size=MANGA_POSTER_MAX_SIZE, 
        allowed_file_types=MANGA_POSTER_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_POSTER_ALLOWED_EXTENSIONS,
        allow_none=True
    )

class UpdateStudioMangaSchema(Schema):
    slug = fields.String()
    name = fields.String()
    name_translations = Json(fields.Nested(CreateUpdateNameTranslationSchema))
    description = fields.String(allow_none=True)
    status_id = fields.Integer()
    type_id = fields.Integer()
    adult_id = fields.Integer()
    genres_ids = fields.List(fields.Integer())
    year = fields.Integer()
    privacy_id = fields.Integer()
    background = File(
        max_file_size=MANGA_BACKGROUND_MAX_SIZE, 
        allowed_file_types=MANGA_BACKGROUND_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_BACKGROUND_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    poster = File(
        max_file_size=MANGA_POSTER_MAX_SIZE, 
        allowed_file_types=MANGA_POSTER_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_POSTER_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    promo_name = File(
        max_file_size=MANGA_PROMO_NAME_MAX_SIZE, 
        allowed_file_types=MANGA_PROMO_NAME_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_PROMO_NAME_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    promo_logo = File(
        max_file_size=MANGA_PROMO_LOGO_MAX_SIZE, 
        allowed_file_types=MANGA_PROMO_LOGO_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_PROMO_LOGO_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    promo_background = File(
        max_file_size=MANGA_PROMO_BACKGROUND_MAX_SIZE, 
        allowed_file_types=MANGA_PROMO_BACKGROUND_ALLOWED_TYPES, 
        allowed_file_ext=MANGA_PROMO_BACKGROUND_ALLOWED_EXTENSIONS,
        allow_none=True
    )
    background_action = fields.Enum(FileAction, by_value=True)
    poster_action = fields.Enum(FileAction, by_value=True)
    promo_name_action = fields.Enum(FileAction, by_value=True)
    promo_logo_action = fields.Enum(FileAction, by_value=True)
    promo_background_action = fields.Enum(FileAction, by_value=True)

class CreateUpdateProfileLinkSchema(Schema):
    name = fields.String()
    link = fields.String()

class UpdateStudioProfileSchema(Schema):
    name = fields.String(required=True)
    slug = fields.String(required=True)
    about = fields.String()
    links = Json(fields.Nested(CreateUpdateProfileLinkSchema))
    avatar_action = fields.Enum(AvatarAction, by_value=True)
    avatar = File(
        max_file_size=PROFILE_AVATAR_MAX_SIZE, 
        allowed_file_types=PROFILE_AVATAR_ALLOWED_TYPES, 
        allowed_file_ext=PROFILE_AVATAR_ALLOWED_EXTENSIONS,
        allow_none=True
    )

class GetStudioProfileSchema(GetProfileSchema):
    pass

class GetStudioProfilePermissionSchema(GetProfilePermissionsSchema):
    pass

class GetStudioCreateChapterFormSchema(Schema):
    name = fields.String()
    chapter = fields.Integer()
    privacy_id = fields.Integer()
    extra_number = fields.Integer()
    pages = fields.List(fields.String())
    blocked_fields = fields.List(fields.String())
