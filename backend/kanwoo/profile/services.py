from pytils.translit import slugify

from kanwoo.image import ImageServiceFactory
from kanwoo.models import FileModel
from kanwoo.file_storage import FileStorageMixin
from kanwoo.uuid import UUIDGenerator
from kanwoo.database import DBTransaction

from .dto import CreateProfileDTO, ProfilePermissionDTO
from .models import Profile, ProfileAvatar
from .repositories import ProfileRepository
from .exceptions import ProfileNotFoundException
from .permissions import ProfileAuthPolicy, ProfilePolicy

class ProfileAvatarService:
    AVATAR_SIZE = (120, 120)

    def __init__(
            self, 
            storage: FileStorageMixin,
            image_service_factory: ImageServiceFactory, 
            profile_repo: ProfileRepository
        ):
        self.image_service_factory = image_service_factory
        self.profile_repo = profile_repo
        self.storage = storage

    def __get_avatar_path(self, uuid, ext):
        return f"profiles/{uuid}{ext}"

    def update_profile_avatar(self, profile, avatar_file):
        image_service = self.image_service_factory.create(avatar_file, "JPEG")

        avatar_resized_file = image_service.resize(self.AVATAR_SIZE)
        avatar_uuid = UUIDGenerator.generate_uuid_v4()
        avatar_path = self.__get_avatar_path(avatar_uuid, ".jpg")

        profile_avatar = ProfileAvatar(
            uuid=avatar_uuid,
            file=FileModel(
                uuid=avatar_uuid,
                path=avatar_path,
                filename=avatar_file.filename,
                mimetype=avatar_resized_file.content_type,
                file_size=len(avatar_resized_file.bytes),
            ),
        )

        self.storage.save(avatar_resized_file, avatar_path)

        self.profile_repo.update_avatar(profile, profile_avatar)


    def delete_profile_avatar(self, profile):
        self.profile_repo.delete_avatar(profile)


class ProfileAuthService:

    def __init__(
            self, 
            profile_repo: ProfileRepository, 
            profile_auth_policy: ProfileAuthPolicy,
            db_transaction: DBTransaction,
            profile_avatar_service: ProfileAvatarService
        ):
        self.profile_repo = profile_repo
        self.profile_auth_policy = profile_auth_policy
        self.db_transaction = db_transaction
        self.profile_avatar_service = profile_avatar_service

    def _get_slug(self, name: str):
        slug = slugify(name)

        # check if slug has been taken
        try:
            i = 1
            while self.system_get_profile_by_slug(slug):
                slug = slugify(name) + str(i)
                i+=1
        except ProfileNotFoundException:
            return slug

    def _create_profile(self, profile_dto: CreateProfileDTO):
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
    
    def user_create_profile(self, user, data: CreateProfileDTO): 
        if user.id != data.owner_id:
            raise ValueError("User must be creator")
        
        return self._create_profile(data)
    
    def system_create_profile(self, data: CreateProfileDTO):
        return self._create_profile(data)
    
    def system_get_profile_by_id(self, profile_id):
        profile = self.profile_repo.system_get_profile_by_id(profile_id)

        if profile is None:
            raise ProfileNotFoundException
        return profile
    
    def system_get_profile_by_slug(self, slug: str) -> Profile:
        profile = self.profile_repo.system_get_profile_by_slug(slug)

        if profile is None:
            raise ProfileNotFoundException

        return profile
        
    def user_get_user_profiles(self, user):
        return self.profile_repo.get_user_profiles(user.id)
    
    def system_check_user_access_for_profile(self, user, profile):
        return self.profile_auth_policy.can_use(user, profile)
        

class ProfileService:

    def __init__(
            self, 
            profile_repo: ProfileRepository,
            profile_policy: ProfilePolicy,
        ):
        self.profile_repo = profile_repo
        self.profile_policy = profile_policy

    def user_get_profile_by_slug(self, profile, slug: str) -> Profile:
        profile = self.profile_repo.user_get_profile_by_slug(slug)

        if profile is None:
            raise ProfileNotFoundException

        return profile
    
    def system_get_profile_by_slug(self, slug):
        profile = self.profile_repo.system_get_profile_by_slug(slug)

        if profile is None:
            raise ProfileNotFoundException

        return profile
    
    def user_get_profile_by_id(self, profile, profile_id):
        profile = self.profile_repo.user_get_profile_by_id(profile_id)

        if profile is None:
            raise ProfileNotFoundException
        return profile

    def user_get_profile_permission(self, actor, profile):
        return ProfilePermissionDTO(
            edit=self.profile_policy.can_edit(actor, profile),
            delete=self.profile_policy.can_delete(actor, profile)
        )